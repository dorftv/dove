## About
fakeapi serves a list of inputs that our frontend fetches on page load

fakeapi emits websockets when inputs are created or deleted so our frontend can react to.

fakeapi emits random status changes so our frontend can react to

## Usage

curl http://localhost:3000/input/add -X "POST" -H "Content-Type: application/json"  -d '{"uid": "input1", "uri": "http://loalhost:88/preview/playlist.m3u8"}
curl http://localhost:3000/input/delete -X "POST" -H "Content-Type: application/json"  -d '{"uid": "input1"}
