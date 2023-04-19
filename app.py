from flask import Flask, render_template, Response, request
import serial
import numpy as np
import cv2
import  imutils
import sys
import pytesseract
import pandas as pd
import time
import openpyxl
import re
import pymongo
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

myclient = pymongo.MongoClient("mongodb+srv://vehicle202:lG36xa1B9CAHic8O@vehicle.bw2givw.mongodb.net/test")

mydb = myclient["numberplate"]
mycol = mydb["registers"]
myusers = mydb["users"]

def gen():
    cap = cv2.VideoCapture('Studio_Project.mp4')
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    save_interval = 5
    
    # ser = serial.Serial('COM4', 9600, timeout=0.1)  
           # 1/timeout is the frequency at which the port is read
    wb = openpyxl.Workbook()
    ws = wb.active
    
    carno=[]
    ws.append(('Time','Car_No'))
    frame_count = 0
    try:
        while(cap.isOpened()):
            ret, image = cap.read()
           
            if ret:
                frame_count += 1
                if frame_count % (fps * save_interval) == 0:
                    
                    # optional 
                    frame_count = 0
            # cv2.imshow('Frame',image)
            # data = ser.readline().decode().strip()


                    image = imutils.resize(image, width=500)

                    

                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    #cv2.imshow("1 - Grayscale Conversion", gray)

                    gray = cv2.bilateralFilter(gray, 11, 17, 17)
                    #cv2.imshow("2 - Bilateral Filter", gray)

                    edged = cv2.Canny(gray, 170, 200)
                    #cv2.imshow("4 - Canny Edges", edged)

                    ( cnts,new ) = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
                    cnts=sorted(cnts, key = cv2.contourArea, reverse = True)[:30] 
                    NumberPlateCnt = None 

                    count = 0
                    for c in cnts:
                            peri = cv2.arcLength(c, True)
                            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                            if len(approx) == 4:  
                                NumberPlateCnt = approx 
                                break

                    # Masking the part other than the number plate
                    mask = np.zeros(gray.shape,np.uint8)
                    new_image = cv2.drawContours(mask,[NumberPlateCnt],0,255,-1)
                    new_image = cv2.bitwise_and(image,image,mask=mask)
                    # cv2.namedWindow("Final_image",cv2.WINDOW_NORMAL)
                    # cv2.imshow("Final_image",new_image)

                    # Configuration for tesseract
                    config = ('-l eng --oem 1 --psm 3')

                    # Run tesseract OCR on image
                    text = pytesseract.image_to_string(new_image, config=config)

                    #Data is stored in CSV file
                    # raw_data = {'date': [time.asctime( time.localtime(time.time()) )], 
                    #         'v_number': [text]}

                    # df = pd.DataFrame(raw_data, columns = ['date', 'v_number'])
                    # df.to_csv('data.csv')
                    if(text!="" and text not in carno):
                        ws.append((time.asctime( time.localtime(time.time()) ),text))
                        carno.append(text)
                        text=re.sub(r'\W+', '', text)   #keeps only alpha numeric
                        x = mycol.insert_one(
                                            {"Time":time.asctime( time.localtime(time.time()) ),
                                            "Car_No":text,
                                            "Camera":"1"
                                            })


                    # Print recognized text
                    # print(text)
            image = imutils.resize(image, width=500,height=500)        
            ret, jpeg = cv2.imencode('.jpg', image)
            frame = jpeg.tobytes()
        
            yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    except:
        wb.save('output.xlsx')
        

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('home.html',msg="")

@app.route('/home',methods=['POST','GET'])
def home():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        x=myusers.find_one({'username':username})
        if( x!=None):
            if(x['password']==password ):
                return render_template('vehicle.html',display="true",display1="false")
            return render_template('home.html',msg='Recheck the Username and Password')   
        else:
            return render_template('home.html',msg='Recheck the Username and Password')       
@app.route('/vehicle')
def vehicle():
    return render_template('vehicle.html',display="true",display1="false")
@app.route('/livefeed')
def livefeed():
    return render_template('live_feed.html')
@app.route('/about')
def about():
    return render_template('about.html')
@app.route('/contact')
def contact():
    return render_template('contact.html')        

@app.route('/video_feed')
def video_feed():
    
    return Response(gen(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/filter', methods=['POST','GET'])
def filter():
    if request.method=='POST':
        carno=request.form['carno']
        print(carno)
    x=mycol.find(
        {
            'Car_No':str(carno)
        }
        )
    x1=[]
    for i in x:
        x2=[]
        for j in i.values() :
            x2.append(str(j))
        x1.append(x2)    
    return render_template('vehicle.html',display="false",display1="true",list1=x1)   

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2204, threaded=True,debug=False)
