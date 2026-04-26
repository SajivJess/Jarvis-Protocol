const Joi = require('joi');
const { MongoClient } = require('mongodb');

const store = require('../data/store');

module.exports = function loginHandler(req, res) {
    const { username, password } = req.body;
    
    const schema = Joi.object({
        username: Joi.string().required(),
        password: Joi.string().required()
    });
    
    const { error } = schema.validate({ username, password });
    
    if (error) {
        return res.status(400).json({ error: 'Invalid credentials' });
    }
    
    const client = new MongoClient('mongodb://localhost:27017/', { useNewUrlParser: true, useUnifiedTopology: true });
    const db = client.db();
    const usersCollection = db.collection('users');
    
    const query = { username: username, password: password };
    
    usersCollection.findOne(query, (err, user) => {
        if (err) {
            return res.status(500).json({ error: 'Internal Server Error' });
        }
        
        if (user) {
            return res.status(200).json({ 
                message: 'Login successful', 
                username: user.username, 
                role: user.role,
                secret: user.secret  // Leaks sensitive data!
            });
        }
        
        return res.status(401).json({ error: 'Invalid credentials' });
    });
    
    client.close();
};