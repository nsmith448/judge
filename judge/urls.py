from django.conf.urls import patterns, include, url
from django.views.generic import DetailView, TemplateView
from judge import models, views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^contest/(?P<contest>[-\w]+)/$', views.ContestView.as_view(), name='contest_home'),
    url(r'^contest/(?P<contest>[-\w]+)/enter/$', views.enter_contest, name='contest_enter'),
    url(r'^contest/(?P<contest>[-\w]+)/scoreboard/$', views.scoreboard, name='scoreboard'),
    url(r'^contest/(?P<contest>[-\w]+)/(?P<slug>[-\w]+)/', include(patterns('',
        url(r'^$', views.ProblemView.as_view(), name='problem_home'),
        url(r'^sample/$', views.ProblemInputOutputView.as_view(), name='problem_sample_io'),
        url(r'^sample/input/$', views.download_sample, {'file': 'input'}, name='problem_sample_input_file'),
        url(r'^sample/output/$', views.download_sample, {'file': 'output'}, name='problem_sample_output_file'),
        url(r'^attempt/(?P<part>.+)/(?P<attempt_pk>\d+)/$', views.SubmitView.as_view(), name='problem_submit'),
        url(r'^attempt/(?P<part>.+)/$', views.start_submit, name='problem_start_submit'),
        url(r'^submissions/$', views.ProblemSubmissions.as_view(), name='problem_submissions'),
        url(r'^clarifications/$', views.ProblemClarifications.as_view(), name='problem_clarifications'),
        url(r'^clarifications/ask/$', views.ProblemAskClarification.as_view(), name='problem_ask_clarification'),
        url(r'^pdf/$', views.download_pdf, {'attach': True}, name='problem_pdf_file'),
        url(r'^pdf/inline/$', views.download_pdf, {'attach': False}, name='problem_pdf_file_frame'),
        url(r'^input/(?P<attempt_pk>\d+)/(?P<randomness>.+)/$', views.download_inputfile, name='problem_input_file'),
    ))),
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': "login.html"}, name="login"),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'next_page': "/"}, name="logout"),

    url(r'^admin/contest/(?P<contest>[-\w]+)/', include(patterns('',
        url(r'^clarifications/$', views.AdminClarificationList.as_view(), name="clarification_list"),
        url(r'^clarifications/(?P<pk>\d+)/$', views.AdminClarificationRespond.as_view(), name="clarification_respond"),
        url(r'^submissions/$', views.AdminSubmissionList.as_view(), name="submission_list"),
        url(r'^submissions/attempt/(?P<attempt_pk>\d+)/$', views.AdminAttemptDetail.as_view(), name="attempt_detail"),
        url(r'^submissions/attempt/(?P<attempt_pk>\d+)/override/(?P<action>.+?)/$', views.admin_attempt_override, name="attempt_override"),
        url(r'^submissions/attempt/(?P<attempt_pk>\d+)/code/$', views.AdminAttemptViewCode.as_view(), name="attempt_code"),
        url(r'^submissions/attempt/(?P<attempt_pk>\d+)/diff/$', views.admin_attempt_diff, name="attempt_diff"),
        url(r'^submissions/attempt/(?P<attempt_pk>\d+)/diff/quick/$', views.admin_attempt_diff, {'quick': True}, name="attempt_diff_quick"),
    ))),
    url(r'^admin/', include(admin.site.urls)),
) + staticfiles_urlpatterns()
