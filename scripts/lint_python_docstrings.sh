#!/bin/bash

# Lint docstrings only against the the diff to avoid too many errors.
# Check only runtime code. Ignore other other errors which are captured by `lint`

# Compare against `main` if no branch was provided
BRANCH="${1:-main}"
# Diff of committed changes (shows only changes introduced by your branch
FILES_WITH_DIFF=`git diff --diff-filter=d $BRANCH...HEAD --name-only -- rasa_sdk`
NB_FILES_WITH_DIFF=`echo $FILES_WITH_DIFF | grep '\S' | wc -l`

if [ "$NB_FILES_WITH_DIFF" -gt 0 ]
then
    poetry run ruff check --select D --diff $FILES_WITH_DIFF
else
    echo "No python files in diff."
fi

echo "Checking for uncommitted changes in rasa_sdk"

# Diff of uncommitted changes for running locally
DEV_FILES_WITH_DIFF=`git diff HEAD --name-only -- rasa_sdk`
NB_DEV_FILES_WITH_DIFF=`echo $DEV_FILES_WITH_DIFF | grep '\S' | wc -l`

if [ "$NB_DEV_FILES_WITH_DIFF" -gt 0 ]
then
    poetry run ruff check --select D --diff $DEV_FILES_WITH_DIFF
fi
