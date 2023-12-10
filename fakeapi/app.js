const express = require('express');
const bodyParser = require('body-parser');
const WebSocket = require('ws');
const yaml = require('js-yaml');
const fs = require('fs');

const app = express();
const port = 3000;

app.use(bodyParser.json());

// Function to generate random UID
const generateUID = () => Math.random().toString(36).substring(2, 10);

// Load configuration from settings.yml
let config;
try {
  config = yaml.load(fs.readFileSync('settings.yml', 'utf8'));
} catch (e) {
  console.error(e);
}

const mixers = config.mixers || []; // Array to store mixers
const inputs = config.inputs || []; // Array to store inputs
const outputs = config.outputs || []; // Array to store outputs

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

// Get mixers endpoint
app.get('/api/mixers', (req, res) => {
  res.json(mixers);
});

// Get inputs endpoint
app.get('/api/inputs', (req, res) => {
  res.json(inputs);
});

// Get outputs endpoint
app.get('/api/outputs', (req, res) => {
  res.json(outputs);
});


// Update mixer and input endpoints
app.put('/api/mixers', (req, res) => {
  const { uid, inputs, width, height } = req.body;
  mixers.push({ uid, inputs, width, height });
  broadcast({ type: 'mixer', channel: 'CREATE', uid, inputs, width, height });
  res.status(201).send({ message: 'Mixer added' });
});

app.put('/api/inputs', (req, res) => {
  const uid = generateUID();
  const uri = 'http://localhost:88/preview/playlist.m3u8';
  const status = statuses[Math.floor(Math.random() * statuses.length)];
  inputs.push({ uid, uri, status });
  broadcast({ 
    type: 'input', 
    channel: 'CREATE', 
    data: { uid, uri, status } 
  });
  res.status(201).send({ message: 'Input added', uid });
});

app.delete('/api/inputs', (req, res) => {
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

// New outputs endpoint
app.put('/api/outputs', (req, res) => {
  const { uid, type, status } = req.body;
  outputs.push({ uid, type, status });
  broadcast({ type: 'output', channel: 'CREATE', uid, type, status });
  res.status(201).send({ message: 'Output added' });
});

app.delete('/api/outputs', (req, res) => {
  const { uid } = req.body;
  const index = outputs.findIndex(output => output.uid === uid);
  if (index !== -1) {
    outputs.splice(index, 1);
    broadcast({ 
      type: 'output', 
      channel: 'DELETE', 
      data: {uid}
    });
    res.send({ message: 'Output deleted' });
  } else {
    res.status(404).send({ message: 'Output not found' });
  }
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

// Function to randomly update output status
function updateRandomOutputStatus() {
  if (outputs.length > 0) {
    const randomIndex = Math.floor(Math.random() * outputs.length);
    const output = outputs[randomIndex];
    output.status = statuses[Math.floor(Math.random() * statuses.length)];
    broadcast({ 
      type: 'output', 
      channel: 'UPDATE', 
      data: { uid: output.uid, type: output.type, status: output.status } 
    });
  }
}

// Set intervals for random status updates
setInterval(updateRandomInputStatus, 1000);
setInterval(updateRandomOutputStatus, 1000);
app.listen(port, '0.0.0.0', () => {
  console.log(`Mixer API running on http://0.0.0.0:${port}`);
});
