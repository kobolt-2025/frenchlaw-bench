"""Tests pour le pipeline (chargement et agrégation, sans appels LLM)."""

from frenchlaw_bench.models.enums import Category, Dimension, SubCategory, TaskType
from frenchlaw_bench.models.result import AggregateScores, TaskResult
from frenchlaw_bench.models.task import Rubric, RubricItem, Task
from frenchlaw_bench.scoring.aggregator import aggregate_scores


def _make_task(number: int, category: Category, task_type: TaskType) -> Task:
    return Task(
        number=number,
        category=category,
        sub_category=SubCategory.CONTRATS,
        task_type=task_type,
        title=f"Tâche {number}",
        prompt="Prompt test",
        rubric=Rubric(
            items=[
                RubricItem(id="S1", dimension=Dimension.STRUCTURE, description="test", points=1),
            ]
        ),
    )


def test_aggregate_single_model() -> None:
    tasks = [
        _make_task(1, Category.DROIT_PRIVE, TaskType.CONSEIL_STRATEGIQUE),
        _make_task(2, Category.CONTENTIEUX, TaskType.REDACTION),
    ]
    results = [
        TaskResult(task_number=1, model_id="test-model", response="r1", answer_score=0.8),
        TaskResult(task_number=2, model_id="test-model", response="r2", answer_score=0.6),
    ]
    aggs = aggregate_scores(tasks, results)
    assert len(aggs) == 1
    assert aggs[0].model_id == "test-model"
    assert aggs[0].answer_score_mean == 0.7
    assert aggs[0].total_tasks == 2


def test_aggregate_multiple_models() -> None:
    tasks = [_make_task(1, Category.DROIT_PRIVE, TaskType.CONSEIL_STRATEGIQUE)]
    results = [
        TaskResult(task_number=1, model_id="model-a", response="r", answer_score=0.9),
        TaskResult(task_number=1, model_id="model-b", response="r", answer_score=0.5),
    ]
    aggs = aggregate_scores(tasks, results)
    assert len(aggs) == 2
    ids = {a.model_id for a in aggs}
    assert ids == {"model-a", "model-b"}


def test_aggregate_by_category() -> None:
    tasks = [
        _make_task(1, Category.DROIT_PRIVE, TaskType.CONSEIL_STRATEGIQUE),
        _make_task(2, Category.DROIT_PRIVE, TaskType.REDACTION),
        _make_task(3, Category.DROIT_EUROPEEN, TaskType.RECHERCHE_JURIDIQUE),
    ]
    results = [
        TaskResult(task_number=1, model_id="m", response="", answer_score=0.8),
        TaskResult(task_number=2, model_id="m", response="", answer_score=0.6),
        TaskResult(task_number=3, model_id="m", response="", answer_score=1.0),
    ]
    aggs = aggregate_scores(tasks, results)
    assert len(aggs) == 1
    agg = aggs[0]
    assert agg.answer_score_by_category["Droit Privé"] == 0.7
    assert agg.answer_score_by_category["Droit Européen"] == 1.0


def test_load_tasks_from_csv() -> None:
    """Test que le CSV des tâches se charge correctement."""
    from frenchlaw_bench.core.loader import load_tasks

    tasks = load_tasks()
    assert len(tasks) == 20

    categories = {t.category for t in tasks}
    assert Category.DROIT_PRIVE in categories
    assert Category.CONTENTIEUX in categories
    assert Category.DROIT_EUROPEEN in categories

    # Vérifier les comptes par catégorie
    prive_count = sum(1 for t in tasks if t.category == Category.DROIT_PRIVE)
    contentieux_count = sum(1 for t in tasks if t.category == Category.CONTENTIEUX)
    europeen_count = sum(1 for t in tasks if t.category == Category.DROIT_EUROPEEN)
    assert prive_count == 8
    assert contentieux_count == 7
    assert europeen_count == 5

    # Vérifier que chaque tâche a un rubric valide
    for task in tasks:
        assert task.rubric.total_positive_points > 0
        assert len(task.rubric.items) >= 8
        assert task.prompt.strip()
