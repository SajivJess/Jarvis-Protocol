// express_app/server.js
const express = require('express');
const path = require('path');
const store = require('./data/store');

const app = express();
app.use(express.json());

// The Route Registry (Allows hot-swapping handlers)
const routeRegistry = {
  login: require('./routes/login'),
  files: require('./routes/files'),
  notes: require('./routes/notes')
};

// Health Check
app.get('/health', (req, res) => res.status(200).json({ status: 'ok' }));

// Method-Specific Route Delegation
app.post('/api/login', (req, res) => routeRegistry.login(req, res));
app.get('/api/files/:filename', (req, res) => routeRegistry.files(req, res));
app.get('/api/notes/:id', (req, res) => routeRegistry.notes(req, res));

// --- INTERNAL CONTROL ENDPOINT (For OpenEnv Only) ---
app.post('/_control/reload', (req, res) => {
  const { routeFile, routeKey } = req.body;

  if (!routeFile || !routeKey) {
    return res.status(400).json({ status: 'error', message: 'Missing routeFile or routeKey' });
  }

  try {
    const fullPath = require.resolve(path.join(__dirname, routeFile));

    // 1. Invalidate Node's module cache
    delete require.cache[fullPath];

    // 2. Load the newly patched file
    const newHandler = require(fullPath);

    // 3. Update the registry
    routeRegistry[routeKey] = newHandler;

    // 4. Reset the in-memory store to prevent state bleeding between episodes
    store.resetStore();

    res.status(200).json({ status: 'reloaded' });
  } catch (err) {
    // If the LLM wrote syntax errors, it gets caught here
    res.status(500).json({ status: 'error', message: err.message, stack: err.stack });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`[Jarvis-Arena] Express backend listening on port ${PORT}`);
});
