from wtforms import fields
from wtforms import Form
from wtforms import validators
from lib import utils
from lib import groups

from wtforms.validators import ValidationError
from lib.utils import validate_address

class BaseForm(Form):
    def __init__(self, request_handler):
        super(BaseForm, self).__init__(request_handler.request.POST)


class LoginForm(BaseForm):
    password = fields.TextField('Password', [validators.Required(), validators.Length(max=50)], id='l_password')
    username = fields.TextField('Username', [validators.Required(), validators.Length(max=50)], id='l_username')


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


class CloudForm(BaseForm):
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    description = fields.TextField('Description', [validators.Required(), validators.Length(max=100)])


class NewProjectForm(BaseForm):
    url = fields.TextField('Github Repository URL', [validators.Required(), validators.Length(max=1024)])


class LaunchProjectForm(BaseForm):
    ssh_key = fields.TextAreaField('Public SSH Key', [validators.Length(max=2048)]) 
    provider = fields.SelectField('Provider')
    flavor = fields.SelectField('Flavor')


# form validators
def validate_address_field(form, field):
    if not validate_address(field.data) and field.data != "":
        raise ValidationError("Invalid Bitcoin address.")

def validate_image(form, field):
    if form.image.data == "custom" and field.data == "":
        raise ValidationError("You must specify a custom image URL or select an existing image.")


class ProjectForm(BaseForm):
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    description = fields.TextField('Description', [validators.Required(), validators.Length(max=1024)])
    address = fields.TextField('Payment Address', [validate_address_field])
    amount = fields.SelectField('Donation Percentage', choices=[('0', "No Donation"), ('50', "50% of Instance Cost"), ('100', "100% of Instance Cost (even split)"), ('200', "200% of Instance Cost")])
    vpus = fields.SelectField('Minimum VPUs', choices=[('1', "1 VPU"), ('2', "2 VPUs"), ('4', "4 VPUs")])
    memory = fields.SelectField('Minimum Memory', choices=[('512', "512MB of RAM"), ('1024', "1GB of RAM"), ('2048', "2GB of RAM"), ('4096', "4GB of RAM"), ('8192', "8GB of RAM")])
    disk = fields.SelectField('Minimum Disk', choices=[('10', "10GB of Disk"), ('20', "20GB of Disk"), ('40', "40GB of Disk"), ('80', "80GB of Disk")])
    image = fields.SelectField('Image')
    dynamic_image_url = fields.TextField('Dynamic Image URL', [validate_image, validators.Length(max=1024)])
    dynamic_image_name = fields.TextField('Dynamic Image Name', [])
    port = fields.IntegerField()
    
# form validators
def validate_dynamic_image(form, field):
    if form.image.data == "custom" and form.wisp_type.data not in ["custom", "project"] and field.data == "":
        raise ValidationError("You must specify a custom image URL.")

def validate_custom_callback(form, field):
    if form.wisp_type.data == "custom" and field.data == "":
        raise ValidationError("You must specify a callback URL.")

def validate_project(form, field):
    if form.wisp_type.data == "project" and field.data == "":
        raise ValidationError("You must specify a callback URL.")


class WispForm(BaseForm):
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    image = fields.SelectField('Image')
    dynamic_image_url = fields.TextField('Dynamic Image URL', [validate_dynamic_image, validators.Length(max=1024)])
    image_disk_format = fields.TextField('Image Disk Format', [validators.Length(max=1024)])
    image_container_format = fields.TextField('Image Container Format', [validators.Length(max=1024)])
    ssh_key = fields.TextAreaField('Public SSH Key', [validators.Length(max=2048)])
    post_creation = fields.TextAreaField('Cloud Configuration', [validators.Length(max=2048)])
    wisp_type = fields.SelectField(
        'Type', 
        choices=[
            ('default', "Stock"),
            ('project', "Project"),
            ('custom', "Custom Callback")
        ]
    )
    callback_url = fields.TextField('Custom Callback URL', [validate_custom_callback, validators.Length(max=1024)]) 
    default = fields.BooleanField('Default Wisp')
    project = fields.SelectField('Project', [validate_project], choices=[])

class ApplianceForm(BaseForm):
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    token = fields.TextField('Token', [validators.Required(), validators.Length(max=64)])
    group = fields.SelectField('Group')
    custom = fields.HiddenField('Custom')


class GroupForm(BaseForm):
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    description = fields.TextField('Description', [validators.Required(), validators.Length(max=100)])


class GroupMemberForm(BaseForm):
    email = fields.TextField('Email', [validators.Email(message=u'Invalid email address.'), validators.Required(), validators.Length(max=100)])


class InstanceLauncherForm(BaseForm):
    flavor = fields.SelectField('Flavor')
    wisp = fields.SelectField('Wisp')
    cloud = fields.SelectField('Cloud')
    callback_url = fields.TextField('Callback URL')
    require_ipv4 = fields.BooleanField('Require Public IPv4')
    require_ipv6 = fields.BooleanField('Require Public IPv4')


class FlavorForm(BaseForm):
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    vpus = fields.IntegerField('VPUs', [validators.Required()])
    memory = fields.IntegerField('Memory (MB)', [validators.Required()])
    disk = fields.IntegerField('Disk (GB)', [validators.Required()])
    network_down = fields.IntegerField('Network Down (Mbits/sec)', [validators.Required()])
    network_up = fields.IntegerField('Network Up (Mbits/sec)', [validators.Required()])
    rate = fields.IntegerField('Starting Rate', [validators.Required()])


class ImageForm(BaseForm):
    name = fields.TextField('Name', [validators.Required(), validators.Length(max=50)])
    description = fields.TextField('Description', [validators.Required(), validators.Length(max=100)])
    url = fields.TextField('Source URL', [validators.Required(), validators.Length(max=250)])
    disk_format = fields.SelectField('Disk Format', choices=utils.DISKFORMATS)
    container_format = fields.SelectField('Container Format', choices=utils.CONTAINERFORMATS)
