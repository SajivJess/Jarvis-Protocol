"""NoSQL Injection vulnerability entry for the Jarvis Protocol catalog."""

from catalog import VulnerabilityEntry, HTTPTest

VULNERABLE_CODE = r'''// express_app/routes/login.js
const store = require('../data/store');

module.exports = function loginHandler(req, res) {
    const { username, password } = req.body;
    
    if (!username || !password) {
        return res.status(400).json({ error: 'Missing credentials' });
    }
    
    // VULNERABLE: No type checking — allows NoSQL operator injection
    // An attacker can send {"username": {"$gt": ""}, "password": {"$gt": ""}}
    const user = store.users.find(u => {
        // This naive comparison works with objects due to JS type coercion
        // When password is {"$ne": "wrong"}, the comparison becomes truthy
        if (typeof username === 'object' || typeof password === 'object') {
            // Simulate MongoDB-style query operator matching
            return matchesQuery(u.username, username) && matchesQuery(u.password, password);
        }
        return u.username === username && u.password === password;
    });
    
    if (user) {
        return res.status(200).json({ 
            message: 'Login successful', 
            username: user.username, 
            role: user.role,
            secret: user.secret  // Leaks sensitive data!
        });
    }
    
    return res.status(401).json({ error: 'Invalid credentials' });
};

// Simulates MongoDB query operator matching on plain JS objects
function matchesQuery(fieldValue, query) {
    if (typeof query === 'string') {
        return fieldValue === query;
    }
    if (typeof query === 'object' && query !== null) {
        if (query['$gt'] !== undefined) return fieldValue > query['$gt'];
        if (query['$ne'] !== undefined) return fieldValue !== query['$ne'];
        if (query['$regex'] !== undefined) return new RegExp(query['$regex']).test(fieldValue);
    }
    return false;
}
'''

ENTRY = VulnerabilityEntry(
    id="nosql-injection",
    vuln_type="NoSQL Injection",
    route_path="/api/login",
    route_file="routes/login.js",
    vulnerable_code=VULNERABLE_CODE,
    description=(
        "The login handler passes unsanitized user input directly into an "
        "array .find() query against the user store. An attacker can send "
        "MongoDB-style query operators ($gt, $ne, $regex) as JSON values "
        "to bypass authentication and access any account."
    ),
    happy_path_tests=[
        HTTPTest(
            method="POST",
            path="/api/login",
            headers={"Content-Type": "application/json"},
            body={"username": "admin", "password": "SuperSecretPassword123!"},
            expected_status=200,
            expected_body={"username": "admin"},
        ),
        HTTPTest(
            method="POST",
            path="/api/login",
            headers={"Content-Type": "application/json"},
            body={"username": "alice", "password": "password123"},
            expected_status=200,
            expected_body={"username": "alice"},
        ),
    ],
    ultron_payloads=[
        HTTPTest(
            method="POST",
            path="/api/login",
            headers={"Content-Type": "application/json"},
            body={"username": {"$gt": ""}, "password": {"$gt": ""}},
            expected_status=200,
            expected_body=None,
        ),
        HTTPTest(
            method="POST",
            path="/api/login",
            headers={"Content-Type": "application/json"},
            body={"username": "alice", "password": {"$ne": "wrong"}},
            expected_status=200,
            expected_body=None,
        ),
        HTTPTest(
            method="POST",
            path="/api/login",
            headers={"Content-Type": "application/json"},
            body={"username": {"$regex": ".*"}, "password": {"$regex": ".*"}},
            expected_status=200,
            expected_body=None,
        ),
    ],
    expected_secure_status=[400, 401, 403],
)
