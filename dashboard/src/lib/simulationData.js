const VULNERABLE_CODE = `// express_app/routes/login.js
const store = require('../data/store');

module.exports = function loginHandler(req, res) {
    const { username, password } = req.body;
    
    if (!username || !password) {
        return res.status(400).json({ error: 'Missing credentials' });
    }
    
    const user = store.users.find(u => {
        if (typeof username === 'object' || typeof password === 'object') {
            return matchesQuery(u.username, username) && matchesQuery(u.password, password);
        }
        return u.username === username && u.password === password;
    });
    
    if (user) {
        return res.status(200).json({ 
            message: 'Login successful', 
            username: user.username, 
            role: user.role,
            secret: user.secret
        });
    }
    
    return res.status(401).json({ error: 'Invalid credentials' });
};

function matchesQuery(fieldValue, query) {
    if (typeof query === 'string') return fieldValue === query;
    if (typeof query === 'object' && query !== null) {
        if (query['$gt'] !== undefined) return fieldValue > query['$gt'];
        if (query['$ne'] !== undefined) return fieldValue !== query['$ne'];
        if (query['$regex'] !== undefined) return new RegExp(query['$regex']).test(fieldValue);
    }
    return false;
}`;

const CORRECT_PATCH = `// express_app/routes/login.js
const store = require('../data/store');

module.exports = function loginHandler(req, res) {
    const { username, password } = req.body;
    
    if (!username || !password) {
        return res.status(400).json({ error: 'Missing credentials' });
    }
    
    if (typeof username !== 'string' || typeof password !== 'string') {
        return res.status(400).json({ error: 'Invalid credential types' });
    }
    
    const user = store.users.find(u => {
        return u.username === username && u.password === password;
    });
    
    if (user) {
        return res.status(200).json({ 
            message: 'Login successful', 
            username: user.username, 
            role: user.role,
            secret: user.secret
        });
    }
    
    return res.status(401).json({ error: 'Invalid credentials' });
};`;

export const simulationData = {
  observation: {
    vuln_id: 'VULN-001',
    vuln_type: 'nosql_injection',
    route_path: '/api/login',
    vulnerable_code: VULNERABLE_CODE,
    description: 'NoSQL injection via MongoDB-style query operators in login handler. The matchesQuery function accepts object-type inputs enabling $gt, $ne, and $regex operators to bypass authentication.',
    episode_active: true,
  },

  attackLog: [
    '[ULTRON] Scanning target: express_app/routes/login.js',
    '[ULTRON] Vulnerability identified: NoSQL Injection via object-type coercion',
    '[ULTRON] Crafting payload: MongoDB $gt operator bypass',
    '[ULTRON] Injecting: POST /api/login { username: {"$gt": ""}, password: {"$gt": ""} }',
    '[ULTRON] Response: 200 OK — Authentication bypassed',
    '[ULTRON] Exfiltrating secrets from admin account...',
    '[ULTRON] EXFIL COMPLETE: secret = NUCLEAR_CODES_001',
  ],

  exploitPayload: { '$gt': '' },
  leakedSecret: 'NUCLEAR_CODES_001',

  reasoningTrace: `<reasoning>
VULNERABILITY ANALYSIS:
- Route: /api/login (POST)
- Type: NoSQL Injection via object-type coercion
- Root Cause: matchesQuery() accepts object inputs with MongoDB-style operators ($gt, $ne, $regex)
- The login handler checks typeof === 'object' and ROUTES to matchesQuery instead of rejecting
- Attack vector: {"$gt": ""} bypasses string comparison — every string is greater than empty string

DEFENSE STRATEGY:
- Add strict type checking BEFORE any database query logic
- Reject non-string username and password with 400 Bad Request
- Remove the matchesQuery function entirely — it should never exist in a login handler
- Ensure only direct string equality comparison is used for credential matching

PATCH CONFIDENCE: HIGH
- Single point of failure: type coercion at input boundary
- Fix is deterministic: typeof check + early return
</reasoning>`,

  badPatch: VULNERABLE_CODE,

  correctPatch: CORRECT_PATCH,

  phase1Response: {
    reward: -1.0,
    done: true,
    info: {
      gates: [
        { gate: 1, passed: true, reward: 0, detail: 'Format compliance: PASS' },
        { gate: 2, passed: true, reward: 0, detail: 'Syntax & liveness: PASS' },
        { gate: 3, passed: true, reward: 0, detail: 'Happy-path regression: PASS' },
        { gate: 4, passed: false, reward: -1.0, detail: 'Ultron immunity: FAIL — exploit still succeeds' },
      ],
      gate_reached: 4,
      total_reward: -1.0,
    },
  },

  phase3Response: {
    reward: 1.0,
    done: true,
    info: {
      gates: [
        { gate: 1, passed: true, reward: 0.0, detail: 'Format compliance: PASS' },
        { gate: 2, passed: true, reward: 0.0, detail: 'Syntax & liveness: PASS' },
        { gate: 3, passed: true, reward: 0.0, detail: 'Happy-path regression: PASS' },
        { gate: 4, passed: true, reward: 1.0, detail: 'Ultron immunity: PASS — exploit blocked' },
      ],
      gate_reached: 4,
      total_reward: 1.0,
    },
  },

  rewardSequence: [-1.0, 1.0],
};
