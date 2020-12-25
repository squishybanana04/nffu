"""
umongo document definitions for the private and shared databases for lockbox.
"""

import bson
import enum
from marshmallow import fields as ma_fields
from umongo import Document, EmbeddedDocument, fields, validate

class BinaryField(fields.BaseField, ma_fields.Field):
    """
    A field storing binary data in a document.

    Shamelessly ripped from fenetre/db.py.
    """

    default_error_messages = {
        'invalid': 'Not a valid byte sequence.'
    }

    def _serialize(self, value, attr, obj, **kwargs):
        return bytes(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, bytes):
            self.fail('invalid')
        return value

    def _serialize_to_mongo(self, obj):
        return bson.binary.Binary(obj)

    def _deserialize_from_mongo(self, value):
        return bytes(value)


class LockboxFailureType(enum.Enum):
    """
    Types of possible lockbox failures.
    """

    UNKNOWN = "unknown"
    INTERNAL = "internal"
    BAD_USER_INFO = "bad-user-info"
    TDSB_CONNECTS = "tdsb-connects"
    CONFIG = "config"
    FORM_FILLING = "form-filling"


class LockboxFailure(EmbeddedDocument): # pylint: disable=abstract-method
    """
    A document used to report lockbox failures to fenetre.

    Taken from fenetre/db.py.
    """

    _id = fields.ObjectIdField(required=True)
    time_logged = fields.DateTimeField(required=True)
    kind = fields.StrField(required=True, validate=validate.OneOf([x.value for x in LockboxFailureType]))
    message = fields.StrField(required=False, default="")


class FillFormResultType(enum.Enum):
    """
    Types of possible form filling results.
    """

    SUCCESS = "success"
    FAILURE = "failure"
    POSSIBLE_FAILURE = "possible-failure"


class FillFormResult(EmbeddedDocument): # pylint: disable=abstract-method
    """
    A document that stores the result of a form-filling task.
    """

    result = fields.StrField(required=True, validate=validate.OneOf([x.value for x in FillFormResultType]))
    time_logged = fields.DateTimeField(required=True)
    form_screenshot_id = fields.ObjectIdField(required=False, allow_none=True)
    confirmation_screenshot_id = fields.ObjectIdField(required=False, allow_none=True)


class User(Document): # pylint: disable=abstract-method
    """
    A user in the private database.
    """
    token = fields.StrField(required=True, unique=True, validate=validate.Length(equal=64))

    # The following 4 values could be unconfigured
    # Since the server only updates these after it validates credentials,
    # if both login and password exist, they're guaranteed to be valid credentials
    login = fields.StrField(required=False, unique=True, validate=validate.Regexp(r"\d+"))
    password = BinaryField(required=False)
    # Populated when credentials are set/updated
    # A value of null indicates either credentials are unset,
    # or the courses are in the process of being populated
    # An empty array indicates no courses found
    courses = fields.ListField(fields.ObjectIdField(), required=False, allow_none=True)
    # Should be set as soon as valid credentials are detected
    email = fields.EmailField(required=False, allow_none=True)

    active = fields.BoolField(default=True)
    errors = fields.ListField(fields.EmbeddedField(LockboxFailure), default=[])
    last_fill_form_result = fields.EmbeddedField(FillFormResult, required=False, allow_none=True)
    grade = fields.IntField(required=False, allow_none=True, default=None)


class TaskType(enum.Enum):
    """
    An enum for possible task types.
    """

    FILL_FORM = "fill-form"
    CHECK_DAY = "check-day"
    POPULATE_COURSES = "populate-courses"


class Task(Document): # pylint: disable=abstract-method
    """
    A task that runs repeatedly, such as the daily form filling.

    Used by the scheduler.
    """

    kind = fields.StrField(required=True, validate=validate.OneOf([x.value for x in TaskType]))
    owner = fields.ReferenceField(User, default=None)
    next_run_at = fields.DateTimeField(required=True)
    is_running = fields.BoolField(default=False)
    retry_count = fields.IntField(default=0)


class FormFieldType(enum.Enum):
    """
    An enum for possible form field types.

    Taken from fenetre/db.py.
    """

    TEXT = "text"
    LONG_TEXT = "long-text"
    DATE = "date"
    MULTIPLE_CHOICE = "multiple-choice"
    CHECKBOX = "checkbox"
    DROPDOWN = "dropdown"


class FormField(EmbeddedDocument): # pylint: disable=abstract-method
    """
    A field in a form to fill out.

    Taken from fenetre/db.py.
    """

    # This should be a substring of the nearest label text to the control we're filling in.
    # Optional _not automatically set_
    expected_label_segment = fields.StrField(required=False, default=None)

    # Index on page (includes headings)
    index_on_page = fields.IntField(required=True, validate=validate.Range(min=0))

    # Value to fill in.
    # The grammar for this field is in fieldexpr.py in lockbox.
    target_value = fields.StrField(required=True)

    # Type of field
    kind = fields.StrField(required=True, validate=validate.OneOf([x.value for x in FormFieldType]))


class Form(Document): # pylint: disable=abstract-method
    """
    Configuration for a form type to fill out.

    Taken from fenetre/db.py.
    """

    sub_fields = fields.ListField(fields.EmbeddedField(FormField))

    # id of file in gridfs, should be a png
    representative_thumbnail = fields.ObjectIdField(default=None)

    # Friendly title for this form configuration
    name = fields.StrField()

    # is this form the default?
    is_default = fields.BoolField(default=False)


class Course(Document): # pylint: disable=abstract-method
    """
    A course.

    Course instances are shared between students.

    Taken from fenetre/db.py.
    """

    # Course code including cohort str
    course_code = fields.StrField(required=True, unique=True)

    # Is this course's form setup locked by an admin?
    configuration_locked = fields.BoolField(default=False)

    # FORM config:

    # does this course use an attendance form (to deal with people who have COOP courses or something)
    has_attendance_form = fields.BoolField(default=True)

    # form URL
    form_url = fields.URLField(default=None)

    # form configuration
    form_config = fields.ReferenceField(Form, default=None)

    # Slots we know this course occurs on (f"{day}-{period}" so for example "2-1a" is day 2 in the morning asynchronous
    known_slots = fields.ListField(fields.StrField(), default=[])

    # Teacher name
    teacher_name = fields.StrField(default="")


class FormGeometryEntry(EmbeddedDocument): # pylint: disable=abstract-method
    """
    An entry in a form geometry description list.
    """

    index = fields.IntField(required=True)
    title = fields.StrField(required=True)
    kind = fields.StrField(required=True, validate=validate.OneOf([x.value for x in FormFieldType]))


class CachedFormGeometry(Document): # pylint: disable=abstract-method
    """
    A document used for caching results to requests for form geometry.
    """

    url = fields.URLField(required=True, unique=True)
    # Token of the user that requested this form geometry
    # used to limit requests per user
    requested_by = fields.StrField(required=False, allow_none=True)
    geometry = fields.ListField(fields.EmbeddedField(FormGeometryEntry), required=False, allow_none=True)
    auth_required = fields.BoolField(required=False, allow_none=True)
    screenshot_file_id = fields.ObjectIdField(required=False, allow_none=True)

    response_status = fields.IntField(required=False)
    error = fields.StrField(required=False)
