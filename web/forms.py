from wtforms import fields
from wtforms import Form
from wtforms import validators
from lib import utils
from lib import groups


class BaseForm(Form):
    def __init__(self, request_handler):
        super(BaseForm, self).__init__(request_handler.request.POST)


class LoginForm(BaseForm):
    password = fields.TextField('Password', [validators.Required(), validators.Length(max=50)], id='l_password')
    username = fields.TextField('Username', [validators.Required(), validators.Length(max=50)], id='l_username')


class AppForm(BaseForm):
    appname = fields.TextField('App_Name', [validators.Required(), validators.Length(max=25)], id='appname')
    appdescription = fields.TextField('App_Description', [validators.Required(), validators.Length(max=140)], id='appdescription')
    appcommand = fields.TextField('App_Command', [validators.Required(), validators.Length(max=13), validators.regexp(utils.ALPHANUMERIC_REGEXP, message='Command string is invalid. Letters and numbers only!')], id='appcommand')
    apppublic = fields.SelectField('Public', [validators.Required()], choices=[('public', 'Public'), ('private', 'Private')])


class BlogArticleForm(BaseForm):
    title = fields.TextField('Article_Title', [validators.Required(), validators.Length(max=50)], id='title')
    summary = fields.TextField('Article_Summary', [validators.Required(), validators.Length(max=140)], id='summary')
    filename = fields.TextField('Article_Filename', [validators.Required(), validators.Length(max=140)], id='filename')
    article_type = fields.SelectField('Article Type', [validators.Required()], id='type', choices=[('post', 'Blog Post'), ('page', 'Page Content'), ('partial', 'Partial Content')])   


class AboutForm(BaseForm):
    email = fields.TextField('Email', [validators.Required(), validators.Length(max=100), validators.regexp(utils.EMAIL_REGEXP, message='Invalid email address.')])
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    message = fields.TextAreaField('Message', [validators.Required(), validators.Length(max=2048)])


class EditProfileForm(BaseForm):
    username = fields.TextField('Username', [validators.Required(), validators.Length(max=50)])
    name = fields.TextField('Name', [validators.Length(max=50)])
    email = fields.TextField('Email', [validators.Required(), validators.Length(max=100), validators.regexp(utils.EMAIL_REGEXP, message='Invalid email address.')])
    last_name = fields.TextField('Last_Name', [validators.Length(max=50)])
    company = fields.TextField('Company')
    country = fields.SelectField('Country', choices=utils.COUNTRIES)
    timezone = fields.SelectField('Timezone', choices=utils.timezones())


class ApplianceForm(BaseForm):
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    token = fields.TextField('Token', [validators.Required(), validators.Length(max=64)])
    group = fields.SelectField('Group')


class FlavorForm(BaseForm):
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    description = fields.TextField('Description', [validators.Required(), validators.Length(max=100)])
    vpus = fields.IntegerField('VPUs', [validators.Required()])
    memory = fields.IntegerField('Memory (MB)', [validators.Required()])
    disk = fields.IntegerField('Disk (GB)', [validators.Required()])
    network = fields.IntegerField('Network (Mbits/sec)', [validators.Required()])
    rate = fields.IntegerField('Starting Rate', [validators.Required()])


class ImageForm(BaseForm):
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    description = fields.TextField('Description', [validators.Required(), validators.Length(max=100)])
    url = fields.TextField('Source URL', [validators.Required(), validators.Length(max=250)])
    size = fields.IntegerField('Size', [validators.Required()])
    diskformat = fields.SelectField('Disk Format', choices=utils.DISKFORMATS)
    containerformat = fields.SelectField('Container Format', choices=utils.CONTAINERFORMATS)