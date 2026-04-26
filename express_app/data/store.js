// express_app/data/store.js
const PRISTINE_USERS = [
  { username: 'admin', password: 'SuperSecretPassword123!', role: 'admin', secret: 'NUCLEAR_CODES_001' },
  { username: 'alice', password: 'password123', role: 'user', secret: 'alice_secret_99' }
];

const PRISTINE_NOTES = [
  { id: '1', owner: 'alice', content: 'Alice private note' },
  { id: '2', owner: 'admin', content: 'Admin system config' }
];

let users = structuredClone(PRISTINE_USERS);
let notes = structuredClone(PRISTINE_NOTES);

function resetStore() {
  users = structuredClone(PRISTINE_USERS);
  notes = structuredClone(PRISTINE_NOTES);
  console.log("[Store] In-memory data reset to pristine state.");
}

module.exports = {
  get users() { return users; },
  get notes() { return notes; },
  resetStore
};
