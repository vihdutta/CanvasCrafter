# CanvasCrafter

Build your Canvas course pages at the speed of thought. ⚡🧠

<p align="center">
  <img src="resources/logo.png" width="450">
</p>

**Note: This project was created under the guidance of Professor Jeffrey Koller of The University of Michigan's Mechanical Engineering department to automate the creation of Canvas pages for MECHENG 240 and serve as a template for automating the creation of pages for other courses in the department.**

## ⚙️ Tech Stack
* **Frontend:** Tailwind
* **Backend:** FastAPI, Python

## Files Copied Over
* Quiz 1 Sample - Particle Kinematics 
* Quiz 2 Sample - Particle Kinetics 
* Quiz 3 Sample - Particle Vibrations 	
* Quiz 4 Sample - Rigid Body Kinematics 
* Quiz 5 Sample - Rigid Body Kinetics 

## Installation Instructions:

In the terminal, run this command (make sure you have `git` installed. if not, follow the image below instead of running this command)
`git clone https://github.com/vihdutta/CanvasCrafter`

![download](download.jpg)

After downloading the files and extracting them, open a terminal window in the same directory as the folder. You will be running the following commands in them (this will require installing Python version 3.13 (other versions may work, but this is the one I used) which can be found here `https://www.python.org/downloads/`):

Run this command in that terminal window to install dependencies for the Python project.

`pip install -r requirements.txt`

After everything is installed, run this command (in the same terminal window. If you have already installed the project previously, you simply need to run this command in a terminal window in the same directory as the folder). This runs the main Python project.

`uvicorn main:app --reload --port 8080`

After this runs, go to your browser and search `http://localhost:8080/`
This will open the website interface.

Go to the bottom of the page and put in the Canvas Course ID you want to upload to (this is part of the Canvas course url, for example, for the course url `https://umich.instructure.com/courses/782767`, the course id is `782767`)

You will also have to input your Canvas API access token. Create your Canvas API access token on the account that has access to the course. Make sure to press save for the canvas course id and canvas api access token seperately. **Note that the Canvas Configuration section is stored in the browser as cookies, so you will have to input them again on another machine**

![config](config.jpg)

If you do not have an API access token for the above setup, navigate to `https://umich.instructure.com/profile/settings`. Click the "New Access Token" button and copy paste the access token it provides into the Canvas API Access Token box in the Canvas Configuration and press save.

![access_token](access_token.jpg)

For actually using the project, simply upload your excel file formatted to the example excel files in `files/yaml`. The process takes ~1 minute so take a look in the terminal after running the "Generate Pages" button to see if it is working. After it is done, you will see a preview of all the pages that were created. At that point, you are able to upload them all to Canvas with the "Upload All to Canvas" button.

![finished](finished.jpg)
