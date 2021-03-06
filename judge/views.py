from django.shortcuts import redirect, render, get_object_or_404
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseNotFound
from django.views.generic import DetailView, ListView, CreateView, UpdateView
from django.views.generic.base import ContextMixin
import django.contrib.messages
from django.contrib.messages.views import SuccessMessageMixin
from judge import models
from judge.util import score
from judge.forms import ClarificationForm, AdminClarificationForm
from sendfile import sendfile
from difflib import HtmlDiff

class ContestantMixin():
    def dipatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            return redirect(reverse('index'))

        if 'contest' in kwargs:
            contest = get_object_or_404(models.Contest, slug=kwargs['contest'])
            if not contest.has_contestant(request.user):
                return redirect(reverse('index'))

        return super().dispatch(request, *args, **kwargs)

class IndexView(ListView):
    model = models.Contest
    template_name = "index.html"

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_authenticated():
            qs = qs.exclude(id__in=self.request.user.contests.all())
        return qs

def enter_contest(request, **kwargs):
    try:
        contest = get_object_or_404(models.Contest, slug=kwargs['contest'])
        user = request.user

        if not contest.has_contestant(user):
            contest.contestants.add(user)
 
        return redirect(reverse("contest_home", kwargs={'contest': contest.slug}))

    except models.Contest.DoesNotExist:
        return redirect(reverse("index", kwargs=kwargs))

class ContestView(DetailView):
    model = models.Contest
    template_name = "contest.html"
    context_object_name = 'contest'
    slug_url_kwarg = 'contest'

class ProblemView(ContestantMixin, DetailView):
    model = models.Problem
    template_name = "problem.html"

class ProblemInputOutputView(DetailView):
    model = models.Problem
    template_name = "sample_io.html"

    def get_context_data(self, object=None, **kwargs):
        sampleinput = []
        sampleoutput = []
        with open(object.sampleinput.url, 'r') as infile:
            sampleinput += infile.readlines()
        with open(object.sampleoutput.url, 'r') as outfile:
            sampleoutput += outfile.readlines()

        ctxt = super().get_context_data(object=object, **kwargs)
        ctxt['sampleinput'] = "".join(sampleinput)
        ctxt['sampleoutput'] = "".join(sampleoutput)

        return ctxt

def start_submit(request, **kwargs):
    user = request.user
    contest = get_object_or_404(models.Contest, slug=kwargs['contest'])
    if not contest.has_contestant(user):
        return reverse("index")

    try:
        part = models.ProblemPart.objects.filter(\
                problem__slug=kwargs['slug'], \
                problem__contest__slug=kwargs['contest'],
                name=kwargs['part']).get()

        att = user.attempts.filter(part=part, status=models.Attempt.IN_PROGRESS).first()
        if att is None:
            att = models.Attempt(part=part, owner=user)
            att.save()
        
        kwargs['attempt_pk'] = att.id
        return redirect(reverse("problem_submit", kwargs=kwargs))

    except models.ProblemPart.DoesNotExist:
        del kwargs['part']
        return redirect(reverse("problem_home", kwargs=kwargs))

class SubmitView(ContestantMixin, UpdateView):
    model = models.Attempt
    template_name = "submit.html"
    fields = ['outputfile', 'sourcefile']
    pk_url_kwarg = "attempt_pk"
    context_object_name = "attempt"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['problem'] = self.object.part.problem
        data['part'] = self.object.part
        return data

    def form_valid(self, form):
        response = super().form_valid(form)
        score(self.object)
        return response

    def get_success_url(self):
        problem = self.object.part.problem
        return reverse('problem_submissions', kwargs={
                'contest': problem.contest.slug,
                'slug': problem.slug
            })

def download_sample(request, contest=None, slug=None, file='input', **kwargs):
    problem = get_object_or_404(models.Problem, contest__slug=contest, slug=slug)
    samplefile = problem.sampleinput if file == 'input' else problem.sampleoutput
    return sendfile(request, samplefile.path, attachment=True, attachment_filename=file+".txt")

def download_inputfile(request, randomness=None, **kwargs):
    attempt = models.Attempt.objects.get(pk=kwargs['attempt_pk'])
    path = attempt.get_inputfile_path()

    if randomness != attempt.randomness:
        return HttpResponseNotFound("404 Not Found")
    
    number = models.Attempt.objects.filter(owner=request.user, part=attempt.part).count()
    attachment_filename = "%s-%d.txt" % (attempt.part.name, number)
    return sendfile(request, path, attachment=True, attachment_filename=attachment_filename)

def download_pdf(request, contest=None, slug=None, attach=True, **kwargs):
    problem = get_object_or_404(models.Problem, contest__slug=contest, slug=slug)

    if problem.contest.has_ended() or request.user.is_authenticated() and problem.contest.has_contestant(request.user):
        return sendfile(request, problem.pdf.path, attachment=attach, attachment_filename=slug+".pdf")

    return HttpResponseNotFound("404 Not Found")

class ProblemSubmissions(ContestantMixin, DetailView):
    model = models.Problem
    template_name = "submissions.html"

    def get_context_data(self, **kwargs):
        ctxt = super().get_context_data(**kwargs)
        myattempts = self.request.user.attempts.filter(part__problem=self.object).all()
        ctxt['attempts'] = myattempts
        return ctxt

class ProblemClarifications(DetailView):
    model = models.Problem
    template_name = "clarifications.html"

    def get_context_data(self, **kwargs):
        ctxt = super().get_context_data(**kwargs)
        clarifications = self.object.clarifications.all()
        ctxt['clarifications'] = clarifications
        return ctxt

class ProblemAskClarification(ContestantMixin, SuccessMessageMixin, CreateView):
    model = models.Clarification
    template_name = "clarification_ask.html"
    success_message = "Your question has been submitted. Please check back later for a reply."
    problem = None
    asker = None

    def dispatch(self, request, *args, **kwargs):
        self.problem = get_object_or_404(models.Problem, contest__slug=kwargs['contest'], slug=kwargs['slug'])
        self.asker = request.user
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class):
        kwargs = super().get_form_kwargs()
        return ClarificationForm(asker=self.asker, problem=self.problem, **kwargs)

    def get_context_data(self, **kwargs):
        ctxt = super().get_context_data(**kwargs)
        ctxt['problem'] = self.problem
        return ctxt

    def get_success_url(self):
        return reverse('problem_home', kwargs={
            'contest': self.problem.contest.slug,
            'slug': self.problem.slug,
        })

class AdminSubmissionList(ListView):
    model = models.Attempt
    template_name = "admin_submissions.html"
    context_object_name = 'attempts'
    contest = None
    paginate_by = 20

    def dispatch(self, *args, **kwargs):
        self.contest = get_object_or_404(models.Contest, slug=kwargs['contest'])
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(part__problem__contest=self.contest)
    
    def get_context_data(self, **kwargs):
        ctxt = super().get_context_data(**kwargs)
        ctxt['contest'] = self.contest
        return ctxt

class AdminAttemptDetail(DetailView):
    model = models.Attempt
    pk_url_kwarg = 'attempt_pk'
    template_name = "admin_attempt_detail.html"
    context_object_name = 'attempt'
    contest = None

    def dispatch(self, *args, **kwargs):
        self.contest = get_object_or_404(models.Contest, slug=kwargs['contest'])
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ctxt = super().get_context_data(**kwargs)
        ctxt['contest'] = self.contest
        ctxt['part'] = self.object.part
        return ctxt

class AdminAttemptViewCode(DetailView):
    model = models.Attempt
    pk_url_kwarg = 'attempt_pk'
    template_name = "admin_attempt_code.html"
    context_object_name = 'attempt'
    contest = None

    def dispatch(self, *args, **kwargs):
        self.contest = get_object_or_404(models.Contest, slug=kwargs['contest'])
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ctxt = super().get_context_data(**kwargs)
        ctxt['contest'] = self.contest
        ctxt['part'] = self.object.part
        
        if self.object.sourcefile:
            with open(self.object.sourcefile.path, 'r') as src:
                ctxt['src'] = "".join(src.readlines())

        return ctxt

def admin_attempt_override(request, contest=None, attempt_pk=None, action=None):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect("/admin/")

    attempt = get_object_or_404(models.Attempt, pk=attempt_pk)
    
    if action == "correct":
        attempt.status = models.Attempt.CORRECT
        attempt.reason = models.Attempt.SCORED_MANUALLY
        attempt.score = attempt.part.points
        attempt.save()
    elif action == "wrong":
        attempt.status = models.Attempt.INCORRECT
        attempt.reason = models.Attempt.SCORED_MANUALLY
        attempt.score = 0
        attempt.save()
    elif action == "auto":
        score(attempt)
        attempt.save()

    return redirect(reverse("attempt_detail", kwargs={'contest': contest, 'attempt_pk': attempt_pk}))

def admin_attempt_diff(request, contest=None, attempt_pk=None, quick=False):
    if not request.user.is_authenticated or not request.user.is_staff:
        return redirect("/admin/")

    attempt = get_object_or_404(models.Attempt, pk=attempt_pk)
    their_lines = []
    my_lines = []

    sizehint = [512] if quick else []

    if attempt.outputfile:
        with open(attempt.outputfile.path) as theirs:
            their_lines = theirs.readlines(*sizehint)

    with open(attempt.get_outputfile_path()) as mine:
        my_lines = mine.readlines(*sizehint)

    differ = HtmlDiff()
    html = differ.make_file(their_lines, my_lines, fromdesc="User's output", todesc="Judge's output")

    return HttpResponse(html, content_type="text/html")

class AdminClarificationList(ListView):
    model = models.Clarification
    template_name = "admin_clarification_list.html"
    context_object_name = 'clarifications'
    contest = None
    paginate_by = 4

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect("/admin/")

        self.contest = get_object_or_404(models.Contest, slug=kwargs['contest'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctxt = super().get_context_data(**kwargs)
        ctxt['contest'] = self.contest
        return ctxt

class AdminClarificationRespond(UpdateView):
    model = models.Clarification
    template_name = "admin_clarification_respond.html"
    form_class = AdminClarificationForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_staff:
            return redirect("/admin/")

        self.contest = get_object_or_404(models.Contest, slug=kwargs['contest'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctxt = super().get_context_data(**kwargs)
        ctxt['contest'] = self.contest
        return ctxt

    def get_success_url(self):
        return reverse("clarification_list", kwargs={
            'contest': self.contest.slug,
        })

def scoreboard(request, contest=None):
    obj = get_object_or_404(models.Contest, slug=contest)


    teams = obj.contestants.all()
    for team in teams:
        team.score = obj.get_score(team)

    teams = sorted(teams, key=lambda t: -t.score)

    return render(request, "scoreboard.html", {'teams': teams, 'contest': obj, 'shownames': obj.has_ended() or request.user.is_staff})
