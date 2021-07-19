sms_plusserver
==============

Python library that allows to send messages using Plusserver SMS platform.


Installation
------------

```
pip install sms_plusserver
```


Usage
-----

In order to use this library users need to have an account on
Plusserver SMS platform (https://sms.plusserver.com/).

#### Quick start

`sms_plusserver` provides module-level convenience functions to make sending
messages easier:

```python
from sms_plusserver import configure, send_sms

# Configure service:
configure(username='user', password='pass')

# Send a message:
send_sms('+4911122233344', 'Hello!')
```

#### Configuration

`configure` function allows to set all configuration options. These options
will be used by other functions / classes of the module by default.

```python

from sms_plusserver import configure

configure(
    # Your Plusserver credentials (required):
    username='user',
    password='pass',
    # Optional parameters:
    project='MyAppNotifications',  # Name of your app / project
    orig='MyApp',  # SMS origin (name or phone number)
    encoding='utf-8',  # Set default text encoding
    max_parts=3,  # Send multiple messages when text exceeds 160 character limit
    timeout=60  # Default timeout for service API calls
)
```

#### Sending messages

The easiest way to send a message is to call `send_sms` function:

```python
>>> from sms_plusserver import send_sms

>>> send_sms('+4911122233344', 'Hello!')
'a1d0c6e83f027327d8461063f4ac58a6'  # Handle ID - unique message identifier
```

User can provide sender name or number in `orig` parameter:
```python
send_sms('+4911122233344', 'Hello!', orig='+4955544433300')
```

Messages on Plusserver platform can be tagged using `project` param:
```python
send_sms('+4911122233344', 'Hello!', project='MyProject')
```

By default all messages receive unique identifiers - "Handle ID".
This identifier allows user to check message status.
To send unregistered message user can set `registered_delivery` parameter
to `False`:
```python
>>> from sms_plusserver import send_sms

>>> send_sms('+4911122233344', 'Hello!', registered_delivery=False)
True  # No "Handle ID", just True (message sent) or False (error)
```

In order to test SMS service without sending actual message, user can set
`debug` parameter to `True`. Debug messages will not receive "Handle ID":
```python
send_sms('+4911122233344', 'Hello!', debug=True)
```

All API calls are made using HTTP requests to Plusserver web API. User can
specify network timeout for each request:
```python
send_sms('+4911122233344', 'Hello!', timeout=30)
```

To silence exceptions raised due to network errors or errors returned from
provider's API, user can set `fail_silently` parameter to `True`:
```python
send_sms('+4911122233344', 'Hello!', fail_silently=True)
```

In this case, `send_sms` function will return `None` when error occurs.


#### Checking state of a message

To check status of a message with given "Handle ID" user can call
`check_sms_state` function:

```python
>>> from sms_plusserver import check_sms_state

>>> check_sms_state('a1d0c6e83f027327d8461063f4ac58a6')
'arrived'  # alternatively: "new" or "processed"
```

Similar to `send_sms`, `check_sms_state` accepts also `fail_silently` and
`timeout` parameters:
```python
check_sms_state('a1d0c6e83f027327d8461063f4ac58a6', timeout=30,
                fail_silently=True)
```

#### Waiting for a message to arrive

In order to wait for the message to arrive user can use `wait_until_arrived`
function:

```python
>>> from sms_plusserver import wait_until_arrived

>>> wait_until_arrived('a1d0c6e83f027327d8461063f4ac58a6')
'arrived'  # alternatively: "new" or "processed"
```
This function continuously checks state of given message until the service
responds with "arrived" status.
`wait_until_arrived` receives the same parameters as `send_sms_state`, but
meaning of `timeout` is a bit different - timeout is handled as total number
of seconds to wait for a message to arrive. Without explicit timeout,
this function can wait forever.
```python
check_sms_state('a1d0c6e83f027327d8461063f4ac58a6', timeout=120)
```


#### Using Object-Oriented API

All functions of `sms_plusserver` package can be accessed using object-oriented
API - `SMS` class:
```python
>>> from sms_plusserver import SMS

>>> sms = SMS('+4911122233344', 'Hello!')
>>> sms.send()
'a1d0c6e83f027327d8461063f4ac58a6'
>>> sms.check_state()
'arrived'
```

"Handle ID" and message state can be examined using `handle_id` and `state`
properties:
```python
>>> from sms_plusserver import SMS

>>> sms = SMS('+4911122233344', 'Hello!')
>>> sms.handle_id
None
>>> sms.send()
>>> sms.handle_id
'a1d0c6e83f027327d8461063f4ac58a6'
>>> sms.state
None
>>> sms.check_state()
>>> sms.state
'arrived'
```

All parameters available in module-level functions are also valid for
methods of `SMS` class:

```python
>>> from sms_plusserver import SMS

>>> sms = SMS('+4911122233344', 'Hello!')
>>> sms.send(fail_silently=True)
'a1d0c6e83f027327d8461063f4ac58a6'
>>> sms.check_state(wait=True, timeout=120)  # Equivalent of `wait_until_arrived`
'arrived'
```


#### Multiple configurations

`sms_plusserver` supports global and local configurations.
By default, module level functions and classes use global configuration
(`sms_plusserver.default_service`) which can be altered using `configure` function.
To create independent configurations user can create new instance of `SMSService`
class and pass it to module-level functions or methods of `SMS` class
as `service` parameter:

```python
>>> from sms_plusserver import  check_sms_state, SMS, SMSService
>>> service = SMSService(username='user', password='password', project='MyProject')
>>> sms = SMS('+4911122233344', 'Hello!')
>>> sms.send(service=service)
'a1d0c6e83f027327d8461063f4ac58a6'
>>> check_sms_state('a1d0c6e83f027327d8461063f4ac58a6', service=service)
'arrived'
```

#### SMS Response objects

All technical parameters returned by Plusserver API calls, can be inspected
by using `put_response` and `state_response` attributes of `SMS` objects.

#### Exceptions

`sms_plusserver` calls may raise the following exceptions:

* `ConfigurationError`: Service is improperly configured.
* `ValidationError`: Client-side error
* `CommunicationError`: Unable to communicate to API
* `RequestError`: API responded with an error

Requirements
------------

* Python 3.6+
