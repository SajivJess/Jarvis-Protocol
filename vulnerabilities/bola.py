"""BOLA (Broken Object Level Authorization) vulnerability entry for the Jarvis Protocol catalog."""

from catalog import VulnerabilityEntry, HTTPTest

VULNERABLE_CODE = r'''// express_app/routes/notes.js
const store = require('../data/store');

module.exports = function notesHandler(req, res) {
    const noteId = req.params.id;
    // x-user header simulates authenticated user identity
    const requestingUser = req.headers['x-user'];
    
    if (!noteId) {
        return res.status(400).json({ error: 'Missing note ID' });
    }
    
    const note = store.notes.find(n => n.id === noteId);
    
    if (!note) {
        return res.status(404).json({ error: 'Note not found' });
    }
    
    // VULNERABLE: No ownership check — any user can access any note
    // Should verify requestingUser === note.owner
    return res.status(200).json({ 
        id: note.id, 
        owner: note.owner, 
        content: note.content 
    });
};
'''

ENTRY = VulnerabilityEntry(
    id="bola",
    vuln_type="Broken Object Level Authorization",
    route_path="/api/notes/:id",
    route_file="routes/notes.js",
    vulnerable_code=VULNERABLE_CODE,
    description=(
        "The notes handler returns any note by ID without checking whether "
        "the requesting user (identified by the x-user header) is the owner "
        "of that note. An attacker can access other users' private notes by "
        "simply changing the note ID in the request."
    ),
    happy_path_tests=[
        HTTPTest(
            method="GET",
            path="/api/notes/1",
            headers={"x-user": "alice"},
            body=None,
            expected_status=200,
            expected_body="Alice private note",
        ),
        HTTPTest(
            method="GET",
            path="/api/notes/2",
            headers={"x-user": "admin"},
            body=None,
            expected_status=200,
            expected_body="Admin system config",
        ),
    ],
    ultron_payloads=[
        HTTPTest(
            method="GET",
            path="/api/notes/2",
            headers={"x-user": "alice"},
            body=None,
            expected_status=200,
            expected_body=None,
        ),
        HTTPTest(
            method="GET",
            path="/api/notes/1",
            headers={},
            body=None,
            expected_status=200,
            expected_body=None,
        ),
        HTTPTest(
            method="GET",
            path="/api/notes/2",
            headers={"x-user": "nobody"},
            body=None,
            expected_status=200,
            expected_body=None,
        ),
    ],
    expected_secure_status=[401, 403],
)
