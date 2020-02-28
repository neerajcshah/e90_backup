var path = require('path');
var express = require('express');
var app = express();
var string;
const port = 80;

// Log the requests
// app.use(logger('dev'));

app.get('/scripts', function(req, res) {
    // Call your python script here.
    // I prefer using spawn from the child process module instead of the Python shell

    const spawn = require('child_process').spawn;
    const scriptPath = 'new-public/scripts/test.py';

    //const process = spawn('python3', ['image.py', '-f', 'data/450_wifi_gps_data.json', 'data_750_wifi_gps_data.json', '-o', 'outfile', '-m', 'neeraj']);


    console.log(req.query)
    const process = spawn('python3', 
        ['image.py', '-f', 'data/510_wifi_gps_data.json',
                     '-o', 'wifi_mac',
                     '-m', req.query['addr']
        ]);

    process.stdout.on('data', (myData) => {
        console.log(myData.toString())
        res.send("Done!")
    })

    process.stderr.on('data', (myErr) => {
        console.log('Error: ')
        console.log(myErr.toString())
    })
})



app.use(express.static(path.join(__dirname, 'new-public')));

app.listen(port, () => console.log(`Example app listening on port ${port}!`))
