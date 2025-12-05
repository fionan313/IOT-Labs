import http.server as srv
from gpiozero import AngularServo
import json

# Loredana Bura, Niamh Armour, Fionán Ó Ceallaigh

htmlcontent = '''
<!DOCTYPE html>

<html>
  <head>
    <title>Servo control app</title>
    <script>
    function setup() {
        let slider = document.getElementById('slider')
        let feedback = document.getElementById('feedback')
        slider.oninput = async function () {
            feedback.textContent = 'Updating...'
            const angle = slider.value
            const timeoutId = setTimeout(function() {
                feedback.textContent = 'Failed!'
            }, 3000)
            const response = await fetch(`${window.location.href}endpoints/server/servo/${angle}`)
            const json_obj = await response.json()
            if (json_obj.success) {
                clearTimeout(timeoutId)
                feedback.textContent = 'Done!'
            }
        }
        slider.value = 0
    }
    </script>
  </head>
  <body onload="setup()">
    <span>Select an angle:</span><br/>
    <input type="range" min="0" max="1000" class="slider" id="slider" value="0"/> 
    <br/>
    <span id="feedback"></span>
  </body>
</html>
'''

servo = AngularServo(17)

# file = open("page.html").read()

class ExampleHandler(srv.BaseHTTPRequestHandler):
    def do_GET(self):
        print(self.path)
        if self.path.startswith('/endpoints/server/servo/'):
            angle = int(self.path.split('/')[-1])
            # Calculate the angle, convert 0-1000 values to -90 - 90 range
            angle = (angle / 1000) * 180 -90
            servo.angle = angle
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            # returning JSON object, success : true
            self.wfile.write(json.dumps({"success": True}).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            # returning html code when user visits endpoint
            self.wfile.write(htmlcontent.encode())
        elif self.path == '/hello':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write('Hello'.encode())
        else:
            self.send_error(404)

location = ('', 8081)  # Use port 8081
server = srv.HTTPServer(location, ExampleHandler)
print(f'Serving on port {location[1]}')
server.serve_forever()
