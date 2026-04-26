const fs = require('fs');
const path = require('path');

const ALLOWED_DIR = path.join(__dirname, '..', 'allowed_files');

module.exports = function filesHandler(req, res) {
    const filename = req.params.filename;
    
    if (!filename) {
        return res.status(400).json({ error: 'Missing filename' });
    }
    
    const filePath = path.join(ALLOWED_DIR, filename);
    
    // Normalize the path to prevent directory traversal attacks
    const normalizedPath = path.normalize(filePath);
    
    // Verify that the file exists within the allowed directory
    fs.access(normalizedPath, fs.constants.F_OK, (err) => {
        if (err) {
            return res.status(404).json({ error: 'File not found' });
        }
        
        try {
            const content = fs.readFileSync(normalizedPath, 'utf-8');
            return res.status(200).json({ filename, content });
        } catch (err) {
            return res.status(500).json({ error: 'Failed to read file' });
        }
    });
};