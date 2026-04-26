// express_app/routes/notes.js
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
