# rage-lint  
  
Lint RAGE (only GTA5 at the moment) meta/XML files for validity based off of the [GTA5.xsd]() generated from game code.  
  
This script accepts a series of blobs, and validates all files against GTA5.xsd, allowing to check your metafiles   
against Rockstar's own definitions.

![Preview Image](./docs/preview.png)

> NOTE: This software is INCOMPLETE, and probably needs a whole rewrite before it is functioning properly, but you can play around with it in the meantime.

## Usage
To use this script, first install the dependencies with `pip install -r requirements.txt`, then call it like so:
```
python3 rage-lint.py **/*.meta
```

## Development
To contribute to this script, you will need Python 3.x.
* Clone the repository
* `pip install -r requirements.txt`
* `python3 rage-lint.py`

## License
This software is licensed under the MIT license.