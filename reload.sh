pip uninstall -y gmadaptor
rm -rf dist
poetry build
pip install dist/gmadaptor-`poetry version -s`-py3-none-any.whl
