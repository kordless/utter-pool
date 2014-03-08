from wtforms import fields
from wtforms import Form
from wtforms import validators
from lib import utils

FIELD_MAXLENGTH = 50 # intended to stop maliciously long input

class BaseForm(Form):
    def __init__(self, request_handler):
        super(BaseForm, self).__init__(request_handler.request.POST)

class LoginForm(BaseForm):
    password = fields.TextField('Password', [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)], id='l_password')
    username = fields.TextField('Username', [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)], id='l_username')

class AppForm(BaseForm):
    appname = fields.TextField('App_Name', [validators.Required(), validators.Length(max=25)], id='appname')
    appdescription = fields.TextField('App_Description', [validators.Required(), validators.Length(max=140)], id='appdescription')
    appcommand = fields.TextField('App_Command', [validators.Required(), validators.Length(max=13), validators.regexp(utils.ALPHANUMERIC_REGEXP, message='Command string is invalid. Letters and numbers only!')], id='appcommand')
    apppublic = fields.SelectField('Public', [validators.Required()], choices=[('public', 'Public'), ('private', 'Private')])


class BlogArticleForm(BaseForm):
    title = fields.TextField('Article_Title', [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)], id='title')
    summary = fields.TextField('Article_Summary', [validators.Required(), validators.Length(max=140)], id='summary')
    article_type = fields.SelectField('Article Type', [validators.Required()], choices=[('post', 'Blog Post'), ('guide', 'Guide'), ('video', 'Video')])   
    pass


class ContactForm(BaseForm):
    email = fields.TextField('Email', [validators.Required(), validators.Length(min=7, max=FIELD_MAXLENGTH), validators.regexp(utils.EMAIL_REGEXP, message='Invalid email address.')])
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=FIELD_MAXLENGTH)])
    message = fields.TextAreaField('Message', [validators.Required(), validators.Length(max=65536)])

class EditProfileForm(BaseForm):
    name = fields.TextField('Name', [validators.Length(max=FIELD_MAXLENGTH)])
    last_name = fields.TextField('Last_Name', [validators.Length(max=FIELD_MAXLENGTH)])
    company = fields.TextField('Company')
    country = fields.SelectField('Country', choices=utils.COUNTRIES)   
    pass