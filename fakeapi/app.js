const express = require('express');
const bodyParser = require('body-parser');
const WebSocket = require('ws');

const app = express();
const port = 3000;

app.use(bodyParser.json());

const mixers = []; // Array to store mixers
const inputs = []; // Array to store inputs

const statuses = ["PLAYING", "PENDING", "PAUSED", "BUFFERING"];

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
  broadcast({ type: 'mixer', channel: 'CREATE', uid, inputs });
  res.status(201).send({ message: 'Mixer added' });
});

// Get mixer endpoint
app.get('/mixer', (req, res) => {
  res.json(mixers);
});

// Add input endpoint
app.post('/input/add', (req, res) => {
  const { uid, uri } = req.body;
  const status = statuses[Math.floor(Math.random() * statuses.length)];
  inputs.push({ uid, uri, status });
  broadcast({ 
    type: 'input', 
    channel: 'CREATE', 
    data: { uid, uri, status } 
  });
  res.status(201).send({ message: 'Input added' });
});

// Delete input endpoint
app.post('/input/delete', (req, res) => {
  const { uid } = req.body;
  const index = inputs.findIndex(input => input.uid === uid);
  if (index !== -1) {
    inputs.splice(index, 1);
    broadcast({ 
      type: 'input', 
      channel: 'DELETE', 
      data: {uid}
    });
    res.send({ message: 'Input deleted' });
  } else {
    res.status(404).send({ message: 'Input not found' });
  }
});

// Get inputs endpoint
app.get('/input', (req, res) => {
  res.json(inputs);
});

// Function to randomly update input status
function updateRandomInputStatus() {
  if (inputs.length > 0) {
    const randomIndex = Math.floor(Math.random() * inputs.length);
    const input = inputs[randomIndex];
    input.status = statuses[Math.floor(Math.random() * statuses.length)];
    broadcast({ 
      type: 'input', 
      channel: 'UPDATE', 
      data: { uid: input.uid, uri: input.uri, status: input.status } 
    });
  }
}

setInterval(updateRandomInputStatus, 5000);

app.listen(port, '0.0.0.0', () => {
  console.log(`Mixer API running on http://0.0.0.0:${port}`);
});
