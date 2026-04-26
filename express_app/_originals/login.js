// express_app/routes/login.js
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
