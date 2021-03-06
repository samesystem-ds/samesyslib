## Common functions for Data Science

[![Build Status](https://travis-ci.org/samesystem-ds/samesyslib.svg?branch=master)](https://travis-ci.org/samesystem-ds/samesyslib) 
[![codecov](https://codecov.io/gh/samesystem-ds/samesyslib/branch/master/graph/badge.svg?token=W6fJRyzkU2)](https://codecov.io/gh/samesystem-ds/samesyslib)
![PyPI](https://img.shields.io/pypi/v/samesyslib)
![PyPI - Downloads](https://img.shields.io/pypi/dm/samesyslib)
![GitHub](https://img.shields.io/github/license/samesystem-ds/samesyslib)

[![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)
[![Python 3.7](https://img.shields.io/badge/python-3.7-blue.svg)](https://www.python.org/downloads/release/python-370/)
[![Python 3.8](https://img.shields.io/badge/python-3.8-blue.svg)](https://www.python.org/downloads/release/python-380/)
[![Python 3.9](https://img.shields.io/badge/python-3.9-blue.svg)](https://www.python.org/downloads/release/python-390/)

Common libs used by SameSystem Data Science team.

#### Example Usage

```python
# /opt/settings/config.yml
database:
  user: 'root'
# ----

from pathlib import Path
from samesyslib.utils import load_config

config_path = Path("/opt/settings/config.yml")
conf = load_config(config_path)

conf['database']['user']
```

#### Install

The latest stable version can always be installed or updated via pip:

```python
pip install samesyslib
```

#### Test Coverage

```bash
pip install pytest-cov
python -m pytest --cov=samesyslib tests
```

#### Development Version

The latest development version can be installed directly from GitHub:

```python
pip install git+https://github.com/samesystem-ds/samesyslib.git
```
 
#### License

Code and documentation are available according to the MIT License
(see [LICENSE](https://github.com/samesystem-ds/samesyslib/blob/master/LICENSE)).
