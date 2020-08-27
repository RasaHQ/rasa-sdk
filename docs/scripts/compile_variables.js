const { readFileSync, writeFileSync } = require('fs');
const toml = require('toml');

const VARIABLES_FILE_PATH = './docs/variables.json';
const PYPROJECT_FILE_PATH = '../pyproject.toml';
const JSON_SPACE_INDENT = 4;

const getRasaSdkVersion = () => {
    const pyproject = readFileSync(PYPROJECT_FILE_PATH).toString();
    return toml.parse(pyproject).tool.poetry.version;
};


const writeVariablesFile = () => {
    const variables = JSON.stringify(
        {
            release: getRasaSdkVersion(),
        },
        null,
        JSON_SPACE_INDENT,
    );
    writeFileSync(VARIABLES_FILE_PATH, variables);
};

console.info(`Computing docs variables and writing to ${VARIABLES_FILE_PATH}`);
writeVariablesFile();
