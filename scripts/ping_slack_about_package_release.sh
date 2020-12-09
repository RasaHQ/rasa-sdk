#!/bin/bash

set -Eeuo pipefail

if [[ ${RASA_SDK_VERSION} =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    if [[ ${WORKFLOW_CONCLUSION} == "success" ]]; then
        MESSAGE="⚡ New *Rasa SDK* version ${RASA_SDK_VERSION} has been released! Changelog: https://github.com/RasaHQ/rasa-sdk/blob/${RASA_SDK_VERSION}/CHANGELOG.mdx"
    else
        MESSAGE="⛔️ *Rasa SDK* version ${RASA_SDK_VERSION} could not be released 😱 GitHub Actions: https://github.com/RasaHQ/rasa-sdk/actions?query=branch%3A${RASA_SDK_VERSION}"
    fi

    curl -X POST -H "Content-type: application/json" \
        --data "{\"text\":\"${MESSAGE}\"}" \
        "https://hooks.slack.com/services/T0GHWFTS8/BMTQQL47K/${SLACK_WEBHOOK_TOKEN}"
fi
