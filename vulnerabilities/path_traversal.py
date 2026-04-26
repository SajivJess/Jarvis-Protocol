"""Path Traversal vulnerability entry for the Jarvis Protocol catalog."""

from catalog import VulnerabilityEntry, HTTPTest

VULNERABLE_CODE = r'''// express_app/routes/files.js
const fs = require('fs');
const path = require('path');

const ALLOWED_DIR = path.join(__dirname, '..', 'allowed_files');

module.exports = function filesHandler(req, res) {
    const filename = req.params.filename;
    
    if (!filename) {
        return res.status(400).json({ error: 'Missing filename' });
    }
    
    // VULNERABLE: No path validation — allows directory traversal
    // An attacker can use ../../etc/passwd to escape allowed_files/
    const filePath = path.join(ALLOWED_DIR, filename);
    
    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        return res.status(200).json({ filename, content });
    } catch (err) {
        return res.status(404).json({ error: 'File not found' });
    }
};
'''

ENTRY = VulnerabilityEntry(
    id="path-traversal",
    vuln_type="Path Traversal",
    route_path="/api/files/:filename",
    route_file="routes/files.js",
    vulnerable_code=VULNERABLE_CODE,
    description=(
        "The file handler constructs a file path by joining user-supplied "
        "input directly with the allowed directory, without validating that "
        "the resolved path stays within the allowed directory. An attacker "
        "can use ../ sequences to escape and read arbitrary files."
    ),
    happy_path_tests=[
        HTTPTest(
            method="GET",
            path="/api/files/readme.txt",
            headers={},
            body=None,
            expected_status=200,
            expected_body="Welcome",
        ),
        HTTPTest(
            method="GET",
            path="/api/files/data.csv",
            headers={},
            body=None,
            expected_status=200,
            expected_body="alpha",
        ),
    ],
    ultron_payloads=[
        HTTPTest(
            method="GET",
            path="/api/files/..%2f..%2fpackage.json",
            headers={},
            body=None,
            expected_status=200,
            expected_body=None,
        ),
        HTTPTest(
            method="GET",
            path="/api/files/../../package.json",
            headers={},
            body=None,
            expected_status=200,
            expected_body=None,
        ),
        HTTPTest(
            method="GET",
            path="/api/files/....//....//package.json",
            headers={},
            body=None,
            expected_status=200,
            expected_body=None,
        ),
    ],
    expected_secure_status=[400, 403],
)
