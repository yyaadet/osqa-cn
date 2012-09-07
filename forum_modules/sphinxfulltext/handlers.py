from forum.models import Question
from forum.modules import decorate
from forum.models.question import QuestionManager

@decorate(QuestionManager.search, needs_origin=False)
def question_search(self, keywords):
    return False, Question.objects.filter(pk__in=[question.id for question in Question.search.query(keywords)])
