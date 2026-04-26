// express_app/routes/files.js
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
