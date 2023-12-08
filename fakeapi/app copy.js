const express = require('express');
const bodyParser = require('body-parser');
const WebSocket = require('ws');

const app = express();
const port = 3000;

app.use(bodyParser.json());

const mixers = []; // Array to store mixers
const inputs = []; // Array to store inputs

// WebSocket server
const wss = new WebSocket.Server({ port: 9999, host: '0.0.0.0' });

// Notify all connected clients
function broadcast(data) {
  wss.clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(data));
    }
  });
}

// Add mixer endpoint
app.post('/mixer/add', (req, res) => {
  const { uid, inputs } = req.body;
  mixers.push({ uid, inputs });
  broadcast({ type: 'mixer', uid, inputs });
  res.status(201).send({ message: 'Mixer added' });
});

// Get mixer endpoint
app.get('/mixer', (req, res) => {
  res.json(mixers);
});

// Add input endpoint
app.post('/input/add', (req, res) => {
  const { uid, uri } = req.body;
  inputs.push({ uid, uri });
  broadcast({ type: 'input', uid, uri });
  res.status(201).send({ message: 'Input added' });
});

// Get inputs endpoint
app.get('/input', (req, res) => {
  res.json(inputs);
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Mixer API running on http://0.0.0.0:${port}`);
});