
# A very simple Flask Hello World app for you to get started with...

from flask import Flask, render_template
import predict
import datetime

app = Flask(__name__)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
@app.route('/')
def hello_world():
    crime_list = ['AGGRAVATED ASSAULT','AUTO THEFT','COMMERCIAL BURGLARY','HOMICIDE','LARCENY','OTHER BURGLARY','RESIDENTIAL BURGLARY','ROBBERY']
    res, date = predict.predict_today_crimes()
    length = len(crime_list)
    return render_template('main.html', date = date, res = res, crime_list = crime_list, length = length)
if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int("5003"),debug=True)
