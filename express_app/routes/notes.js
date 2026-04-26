module.exports = function notesHandler(req, res) {
    const noteId = req.params.id;
    const requestingUser = req.headers['x-user'];
    
    if (!noteId) {
        return res.status(400).json({ error: 'Missing note ID' });
    }
    
    const note = store.notes.find(n => n.id === noteId);
    
    if (!note) {
        return res.status(404).json({ error: 'Note not found' });
    }
    
    // Fix: Verify ownership
    if (requestingUser !== note.owner) {
        return res.status(403).json({ error: 'Forbidden: You do not own this note' });
    }
    
    return res.status(200).json({ 
        id: note.id, 
        owner: note.owner, 
        content: note.content 
    });
};