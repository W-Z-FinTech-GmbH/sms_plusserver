import collections
import datetime
import logging
from typing import Optional, Union

import requests
import time


logger = logging.getLogger('sms_plusserver')

# SMS state choices:
STATE_NEW = 'new'
STATE_PROCESSED = 'processed'
STATE_ARRIVED = 'arrived'
STATE_RETRY = 'retry'
STATE_ERROR = 'error'

# SMS response message choices:
MESSAGE_OK = 'REQUEST OK'
MESSAGE_ERROR = 'ERROR'


class SMSServiceError(Exception):
    """Base exception class"""

    def __init__(
        self,
        message: Optional[str] = None,
        original_exception: Optional[str] = None,
    ):
        message = message or str(original_exception)
        super().__init__(message)
        self.original_exception = original_exception

    def is_timeout(self):
        """Is this error caused by timeout?"""
        return self.original_exception and isinstance(
            self.original_exception, requests.Timeout
        )


class ConfigurationError(SMSServiceError):
    """Service is improperly configured"""


class ValidationError(SMSServiceError):
    """Client-side error"""


class CommunicationError(SMSServiceError):
    """Unable to communicate to API"""


class RequestError(SMSServiceError):
    """API responded with an error"""


class SMSResponse(object):
    """Wrapper over SMSService response data, providing dict-like access"""

    def __init__(self, response_text: str):
        lines = response_text.splitlines()
        self.message = lines.pop(0) if lines else ''
        self._data = collections.OrderedDict()
        for line in lines:
            if '=' in line:
                key, value = line.split('=', 1)
                self._data[key.strip()] = value.strip()

    def __repr__(self):
        return f'<{self.__class__.__name__} [{self.message or ""}]>'

    def __getitem__(self, item):
        return self._data[item]

    def __iter__(self):
        return iter(self._data)

    def items(self):
        return self._data.items()

    def get(self, key, default=None):
        try:
            value = self[key]
        except KeyError:
            value = default
        return value

    @property
    def handle_id(self):
        """SMS unique handle ID"""
        return self.get('handle')

    @property
    def state(self):
        """Current state of sent SMS"""
        return self.get('state')

    @property
    def error(self):
        """Error message"""
        return self.get('error')

    @property
    def is_ok(self):
        """Is this an OK response? (based on received message)"""
        return self.message == MESSAGE_OK

    @property
    def is_error(self):
        """Is this an ERROR response? (based on received message)"""
        return self.message == MESSAGE_ERROR


class SMSService(object):
    """Main object - provider's API client"""

    SMS_PUT_URL = 'https://sms.plusserver.com/put.php'
    SMS_STATE_URL = 'https://sms.plusserver.com/sms-state.php'
    CHECK_STATE_WAIT_BETWEEN_CALLS = 0.5

    def __init__(
        self,
        put_url: Optional[str] = None,
        sms_state_url: Optional[str] = None,
        project: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        orig: Optional[str] = None,
        encoding: Optional[str] = None,
        max_parts: Optional[int] = None,
        timeout: Optional[float] = None,
    ):
        """Initializes SMSService object

        :param put_url: SMS sending webservice URL
        :param sms_state_url: SMS state check webservice URL
        :param project: name of the project
        :param username: user name for access to Plusserver platform - REQUIRED
        :param password: password for access to Plusserver platform - REQUIRED
        :param orig: SMS sender ID (optional)
        :param encoding: SMS text encoding,
            choices: 'iso', 'gsm', 'utf-8', 'ucs2'
            (optional, implicit default - 'iso')
        :param max_parts: The maximum number of discrete SMS, to which a long
            text-SMS (>160 chars) will be split
            (optional, implicit default - 1)
        :param timeout: network timeout in seconds (optional)
        """
        self.put_url = put_url or self.SMS_PUT_URL
        self.sms_state_url = sms_state_url or self.SMS_STATE_URL
        self.project = project or ''
        self.username = username
        self.password = password
        self.orig = orig
        self.encoding = encoding
        self.max_parts = max_parts
        self.timeout = timeout

    def __repr__(self):
        project = f' @ {self.project}' if self.project else ''
        return f'<{self.__class__.__name__} {self.username}{project}>'

    def configure(self, **kwargs):
        """Allows to change SMSService parameters set in constructor.

        Available options:
        `put_url`: SMS sending webservice URL
        `sms_state_url`: SMS state check webservice URL
        `project`: name of the project
        `username`: user name for access to Plusserver platform - REQUIRED
        `password`: password for access to Plusserver platform - REQUIRED
        `orig`: SMS sender ID (optional)
        `timeout`: network timeout in seconds (optional)
        """
        for name, value in kwargs.items():
            setattr(self, name, value)

    # High-level API:

    def send(
        self,
        sms: 'SMS',
        timeout: Optional[float] = None,
        fail_silently: bool = False,
    ) -> Union[str, bool]:
        """Sends SMS via Plusserver SMS platform by calling `put_sms`.
        Populates `SMS.put_response` attribute.

        :param sms: a SMS instance
        :param timeout: network timeout in seconds
        :param fail_silently: do not raise exceptions

        :raise ConfigurationError: client is improperly configured
        :raise RequestError: remote API responded with error message or
            HTTP error status
        :raise CommunicationError: unable to communicate with remote API

        :return handle_id if available, boolean success indicator otherwise
        """
        try:
            put_response = self.put_sms(
                destination=sms.destination,
                text=sms.text,
                orig=sms.orig,
                registered_delivery=sms.registered_delivery,
                debug=sms.debug,
                project=sms.project,
                encoding=sms.encoding,
                max_parts=sms.max_parts,
                timeout=timeout,
                fail_silently=fail_silently,
            )
        except Exception:
            sms.put_response = None
            raise
        else:
            sms.put_response = put_response
        if sms.registered_delivery and not sms.debug:
            result = put_response.handle_id if put_response else None
        else:
            result = bool(put_response and put_response.is_ok)
        return result

    def check_state(
        self,
        sms: 'SMS',
        wait: bool = False,
        timeout: Optional[float] = None,
        fail_silently: bool = False,
    ) -> Optional[str]:
        """Checks state of given SMS on Plusserver SMS platform by calling
        `check_sms_status`.
        Populates `SMS.state_response` attribute.

        :param sms: a SMS instance
        :param wait: should we wait for SMS to get 'arrived' state?
        :param timeout: network timeout in seconds
        :param fail_silently: do not raise exceptions

        :raise ConfigurationError: client is improperly configured
        :raise ValidationError: invalid request attempt
        :raise RequestError: remote API responded with error message or
            HTTP error status
        :raise CommunicationError: unable to communicate with remote API

        :return state if available, None otherwise
        """
        method = self.wait_until_arrived if wait else self.check_sms_state
        try:
            state_response = method(
                handle_id=sms.handle_id,
                timeout=timeout,
                fail_silently=fail_silently,
            )
        except Exception:
            sms.state_response = None
            raise
        else:
            sms.state_response = state_response
        return state_response.state if state_response else None

    # Low-level API:

    def put_sms(
        self,
        destination: str,
        text: str,
        orig: Optional[str] = None,
        registered_delivery: bool = True,
        debug: bool = False,
        project: Optional[str] = None,
        encoding: Optional[str] = None,
        max_parts: Optional[int] = None,
        timeout: Optional[float] = None,
        fail_silently: bool = False,
    ) -> Optional[SMSResponse]:
        """Sends SMS via Plusserver SMS platform.

        :param destination: recipient ID (phone number)
        :param text: message to be sent
        :param orig: SMS sender ID (optional)
        :param registered_delivery: boolean to denote if delivery should be
            registered on Plusserver platform in order to allow state checking
        :param debug: simulate SMS sending
        :param project: a category, to be displayed in message logs on
            Plusserver platform
        :param encoding: SMS text encoding,
            choices: 'iso', 'gsm', 'utf-8', 'ucs2'
            (optional, implicit default - 'iso')
        :param max_parts: The maximum number of discrete SMS, to which a long
            text-SMS (>160 chars) will be split
            (optional, implicit default - 1)
        :param timeout: network timeout in seconds
        :param fail_silently: do not raise exceptions

        :raise ConfigurationError: client is improperly configured
        :raise RequestError: remote API responded with error message or
            HTTP error status
        :raise CommunicationError: unable to communicate with remote API

        :return a SMSResponse object or None
        """
        if not (self.username and self.password):
            raise ConfigurationError('Service credentials not defined')

        auth = (self.username, self.password)

        data = {
            'dest': destination,
            'data': text,
            'debug': str(int(debug)),
            'project': project or self.project,
            'registered_delivery': str(int(registered_delivery)),
        }
        orig = orig or self.orig
        if orig:
            data['orig'] = orig
        encoding = encoding or self.encoding
        if encoding:
            data['enc'] = encoding
        max_parts = max_parts or self.max_parts
        if max_parts:
            data['maxparts'] = str(max_parts)

        if timeout is None:
            timeout = self.timeout

        return self._request(
            url=self.put_url,
            data=data,
            auth=auth,
            timeout=timeout,
            resource_name='Put SMS',
            fail_silently=fail_silently,
        )

    def check_sms_state(
        self,
        handle_id: str,
        timeout: Optional[float] = None,
        fail_silently: bool = False,
    ) -> Optional[SMSResponse]:
        """Checks state of given SMS (Handle ID) on Plusserver SMS platform.

        :param handle_id: SMS unique identifier on Plusserver platform
        :param timeout: network timeout in seconds
        :param fail_silently: do not raise exceptions

        :raise ConfigurationError: client is improperly configured
        :raise ValidationError: invalid request attempt
        :raise RequestError: remote API responded with error message or
            HTTP error status
        :raise CommunicationError: unable to communicate with remote API

        :return a SMSResponse object or None
        """
        if not (self.username and self.password):
            raise ConfigurationError('Service credentials not defined')
        if not handle_id:
            raise ValidationError('Unable to check state of unsent SMS')

        auth = (self.username, self.password)

        data = {'handle': handle_id}

        if timeout is None:
            timeout = self.timeout

        return self._request(
            url=self.sms_state_url,
            data=data,
            auth=auth,
            timeout=timeout,
            resource_name='Check SMS state',
            fail_silently=fail_silently,
        )

    def wait_until_arrived(
        self,
        handle_id: str,
        timeout: Optional[float] = None,
        fail_silently: bool = False,
    ) -> Optional[SMSResponse]:
        """Waits until SMS (Handle ID) gets 'arrived' state on Plusserver SMS
        platform.

        :param handle_id: SMS unique identifier on Plusserver platform
        :param timeout: network timeout in seconds
        :param fail_silently: do not raise exceptions

        :raise ConfigurationError: client is improperly configured
        :raise ValidationError: invalid request attempt
        :raise RequestError: remote API responded with error message or
            HTTP error status
        :raise CommunicationError: unable to communicate with remote API

        :return a SMSResponse object or None
        """
        remaining_timeout = timeout if timeout else self.timeout
        start = datetime.datetime.now()
        state_response = None
        while remaining_timeout is None or remaining_timeout > 0:
            step_start = datetime.datetime.now()
            try:
                state_response = self.check_sms_state(
                    handle_id, timeout=remaining_timeout, fail_silently=False
                )
            except SMSServiceError as error:
                if not error.is_timeout() and not fail_silently:
                    raise
                else:
                    break
            else:
                step_end = datetime.datetime.now()
                if state_response.state == STATE_ARRIVED:
                    logger.debug(
                        'SMS [{}] arrived. Total delay: {}'.format(
                            handle_id, step_end - start
                        )
                    )
                    break
                logger.debug(
                    'SMS [{}] not arrived yet. Total delay: {}'.format(
                        handle_id, step_end - start
                    )
                )
                if remaining_timeout is not None:
                    step_duration = step_start - step_end
                    remaining_timeout -= step_duration.total_seconds()
                    wait_secs = self.CHECK_STATE_WAIT_BETWEEN_CALLS
                    if remaining_timeout > wait_secs * 1.5:
                        time.sleep(wait_secs)
        return state_response

    @staticmethod
    def _request(
        url: str,
        data: dict,
        auth: dict,
        timeout: float,
        resource_name: str,
        fail_silently: bool,
    ) -> Optional[SMSResponse]:
        """Sends a request to Service API, construct SMSResponse object from
        response.

        :param url: destination's URL address
        :param data: POST data
        :param auth: HTTP Basic Auth data
        :param timeout: network timeout in seconds
        :param resource_name: destination's verbose name (for logging)
        :param fail_silently: do not raise exceptions

        :raise RequestError: remote API responded with error message or
            HTTP error status
        :raise CommunicationError: unable to communicate with remote API

        :return a SMSResponse object or None
        """
        try:
            response = requests.post(url, data, auth=auth, timeout=timeout)
            logger.debug(
                '{} response: {} {}'.format(
                    resource_name, response.status_code, response.reason
                )
            )
            response.raise_for_status()
        except requests.RequestException as error:
            if isinstance(error, requests.HTTPError):
                exception_class = RequestError
            else:
                exception_class = CommunicationError
            exception = exception_class(original_exception=error)
            logger.error(exception)

            sms_response = None
            if not fail_silently:
                raise exception
        else:
            sms_response = SMSResponse(response.text)
            if sms_response.is_error:
                exception = RequestError(sms_response.error)
                logger.error(exception)

                sms_response = None
                if not fail_silently:
                    raise exception

        return sms_response


default_service = SMSService()


class SMS(object):
    """Single message wrapper"""

    def __init__(
        self,
        destination: str,
        text: str,
        orig: Optional[str] = None,
        registered_delivery: bool = True,
        debug: bool = False,
        project: Optional[str] = None,
        encoding: Optional[str] = None,
        max_parts: Optional[int] = None,
    ):
        """Initializes SMS object - a single message

        :param destination: recipient ID (phone number)
        :param text: message to be sent
        :param orig: SMS sender ID (optional)
        :param registered_delivery: boolean to denote if delivery should be
            registered on Plusserver platform in order to allow state checking
        :param debug: simulate SMS sending
        :param project: a category, to be displayed in message logs on
            Plusserver platform
        :param encoding: SMS text encoding,
            choices: 'iso', 'gsm', 'utf-8', 'ucs2'
            (optional, implicit default - 'iso')
        :param max_parts: The maximum number of discrete SMS, to which a long
            text-SMS (>160 chars) will be split
            (optional, implicit default - 1)
        """
        self.destination = destination
        self.text = text
        self.orig = orig
        self.registered_delivery = registered_delivery
        self.debug = debug
        self.project = project
        self.encoding = encoding
        self.max_parts = max_parts
        self.put_response = None
        self.state_response = None

    def __repr__(self):
        handle_id = f' [{self.handle_id}]' if self.handle_id else ''
        state = f' {self.state}' if self.state else ''
        class_name = self.__class__.__name__
        return f'<{class_name} {self.destination}{handle_id}{state}>'

    def send(
        self,
        timeout: Optional[float] = None,
        fail_silently: bool = False,
        service: Optional[SMSService] = None,
    ) -> Union[str, bool]:
        """Sends this SMS.

        :param timeout: network timeout in seconds
        :param fail_silently: do not raise exceptions
        :param service: a SMSService instance

        :raise ConfigurationError: client is improperly configured
        :raise RequestError: remote API responded with error message or
            HTTP error status
        :raise CommunicationError: unable to communicate with remote API

        :return handle_id if available, boolean success indicator otherwise
        """
        service = service or default_service
        return service.send(self, timeout=timeout, fail_silently=fail_silently)

    def check_state(
        self,
        wait: bool = False,
        timeout: Optional[float] = None,
        fail_silently: bool = False,
        service: Optional[SMSService] = None,
    ) -> Optional[str]:
        """Checks state of this SMS.

        :param wait: perform subsequent checks until 'arrived' state received
        :param timeout: network timeout in seconds
        :param fail_silently: do not raise exceptions
        :param service: a SMSService instance

        :raise ConfigurationError: client is improperly configured
        :raise ValidationError: invalid request attempt
        :raise RequestError: remote API responded with error message or
            HTTP error status
        :raise CommunicationError: unable to communicate with remote API

        :return state if available, None otherwise
        """
        service = service or default_service
        return service.check_state(
            self, wait=wait, timeout=timeout, fail_silently=fail_silently
        )

    @property
    def handle_id(self) -> Optional[str]:
        """SMS unique handle ID"""
        return self.put_response.handle_id if self.put_response else None

    @property
    def state(self) -> Optional[str]:
        """Current state of sent SMS"""
        response = self.state_response or self.put_response
        return response.state if response else None


# Shortcut functions, bypassing OOP API:


def send_sms(
    destination: str,
    text: str,
    orig: Optional[str] = None,
    registered_delivery: bool = True,
    debug: bool = False,
    project: Optional[str] = None,
    encoding: Optional[str] = None,
    max_parts: Optional[int] = None,
    timeout: Optional[float] = None,
    fail_silently: bool = False,
    service: Optional[SMSService] = None,
) -> Union[str, bool]:
    """Shortcut to send a SMS.

    :param destination: recipient ID (phone number)
    :param text: message to be sent
    :param orig: SMS sender ID (optional)
    :param registered_delivery: boolean to denote if delivery should be
        registered on Plusserver platform in order to allow state checking
    :param debug: simulate SMS sending
    :param project: a category, to be displayed in message logs on Plusserver
        platform
    :param encoding: SMS text encoding,
        choices: 'iso', 'gsm', 'utf-8', 'ucs2'
        (optional, implicit default - 'iso')
    :param max_parts: The maximum number of discrete SMS, to which a long
        text-SMS (>160 chars) will be split
        (optional, implicit default - 1)
    :param timeout: network timeout in seconds
    :param fail_silently: do not raise exceptions
    :param service: a SMSService instance

    :raise ConfigurationError: client is improperly configured
    :raise RequestError: remote API responded with error message or
        HTTP error status
    :raise CommunicationError: unable to communicate with remote API

    :return handle_id if available, boolean success indicator otherwise
    """
    sms = SMS(
        destination=destination,
        text=text,
        orig=orig,
        registered_delivery=registered_delivery,
        debug=debug,
        project=project,
        encoding=encoding,
        max_parts=max_parts,
    )
    return sms.send(
        timeout=timeout, fail_silently=fail_silently, service=service
    )


def check_sms_state(
    handle_id: str,
    timeout: Optional[float] = None,
    fail_silently: bool = False,
    service: Optional[SMSService] = None,
) -> Optional[str]:
    """Shortcut to check state of a SMS.

    :param handle_id: SMS unique identifier on Plusserver platform
    :param timeout: network timeout in seconds
    :param fail_silently: do not raise exceptions
    :param service: a SMSService instance

    :raise ConfigurationError: client is improperly configured
    :raise ValidationError: invalid request attempt
    :raise RequestError: remote API responded with error message or
        HTTP error status
    :raise CommunicationError: unable to communicate with remote API

    :return state if available, None otherwise
    """
    service = service or default_service
    state_response = service.check_sms_state(
        handle_id, timeout=timeout, fail_silently=fail_silently
    )
    return state_response.state if state_response else None


def wait_until_arrived(
    handle_id: str,
    timeout: Optional[float] = None,
    fail_silently: bool = False,
    service: Optional[SMSService] = None,
) -> Optional[str]:
    """Waits until SMS gets 'arrived' status.

    :param handle_id: SMS unique identifier on Plusserver platform
    :param timeout: network timeout in seconds
    :param fail_silently: do not raise exceptions
    :param service: a SMSService instance

    :raise ConfigurationError: client is improperly configured
    :raise ValidationError: invalid request attempt
    :raise RequestError: remote API responded with error message or
        HTTP error status
    :raise CommunicationError: unable to communicate with remote API

    :return state if available, None otherwise
    """
    service = service or default_service
    state_response = service.wait_until_arrived(
        handle_id, timeout=timeout, fail_silently=fail_silently
    )
    return state_response.state if state_response else None


def configure(**kwargs):
    """Configures default SMSService instance.

    Available options:
    `put_url`: SMS sending webservice URL
    `sms_state_url`: SMS state check webservice URL
    `project`: name of the project
    `username`: user name for access to Plusserver platform - REQUIRED
    `password`: password for access to Plusserver platform - REQUIRED
    `orig`: SMS sender ID (optional)
    `timeout`: network timeout in seconds (optional)
    """
    default_service.configure(**kwargs)
