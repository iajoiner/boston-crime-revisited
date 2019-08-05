import numpy as np
import pandas as pd
import requests
import datetime
import calendar
import pickle
import json
import re
from bs4 import BeautifulSoup
import holidays
def intize(string):
    try:
        num = int(string)
        return num
    except ValueError as e:
        return None
def floatize(string):
    try:
        num = float(string)
        return num
    except ValueError as e:
        return None
def sum_with_null(string_list):
    res = 0.0
    for string in string_list:
        nullable_num = floatize(string)
        if isinstance(nullable_num, float):
            res = res + nullable_num
    return res
def max_with_null(string_list):
    res = None
    is_nonnull = False
    for string in string_list:
        nullable_num = intize(string)
        if isinstance(nullable_num, int):
            if not is_nonnull:
                res = nullable_num
                is_nonnull = True
            else:
                if res < nullable_num:
                    res = nullable_num
    return res
def min_with_null(string_list):
    res = None
    is_nonnull = False
    for string in string_list:
        nullable_num = intize(string)
        if isinstance(nullable_num, int):
            if not is_nonnull:
                res = nullable_num
                is_nonnull = True
            else:
                if res > nullable_num:
                    res = nullable_num
    return res
def wind_speed_extractor(string):
    str_list = string.split()
    for str_ in str_list:
        try:
            num = int(str_)
            return num
        except ValueError as e:
            continue
    return 0#No number
def ave_wind_speed_extractor(string_list):
    leng = len(string_list)
    return sum(list(map(wind_speed_extractor, string_list)))/leng
def snow_amount_extractor(desc_list, prec_list):
    len1 = len(desc_list)
    len2 = len(prec_list)
    if len1 != len2:
        raise ValueError(f'{desc_list} and {prec_list} have different sizes!')
    snow_total = 0.0
    for ind in range(len1):
        if 'Snow' in desc_list[ind] or 'snow' in desc_list[ind]:
            snow_total = snow_total + floatize(prec_list[ind])
    return snow_total
def newest_day_weather(loc = 'KBOS'):
    recent_weather_url = 'https://w1.weather.gov/data/obhistory/' + loc + '.html'
    rw_req = requests.get(recent_weather_url)
    rw_req.raise_for_status()
    if rw_req.status_code == requests.codes.ok:
        soup = BeautifulSoup(rw_req.text, 'html.parser')
        table = soup.find_all('table')[3]
        rows = table.find_all('tr')
        num_rows = len(rows)
        data_dic_list = []
        for ind in range(3, num_rows):#Skip the first three rows
            row = rows[ind]
            pre_data_list = row.find_all('td')
            data_list = [pre_data.text for pre_data in pre_data_list]
            if len(data_list) == 0:
                break
            data_dic = {'day':data_list[0],'hour':data_list[1][:2],'wind':data_list[2], 'description': data_list[4], 'six_max':data_list[8], 'six_min':data_list[9], 'one_prec': data_list[15]}
            data_dic_list.append(data_dic)
        df_recent_weather = pd.DataFrame(data_dic_list)
        day = df_recent_weather.iat[0,df_recent_weather.columns.get_loc('day')]
        last_hour = df_recent_weather.iat[0,df_recent_weather.columns.get_loc('hour')]
        temp_dic = {'day':int(day)}
        df_temp_day = df_recent_weather[df_recent_weather.day == day]
        #print(df_temp_day.dtypes)
        temp_dic['PRCP'] = sum_with_null(df_temp_day['one_prec'].tolist())
        temp_dic['TMAX'] = max_with_null(df_temp_day['six_max'].tolist())
        temp_dic['TMIN'] = min_with_null(df_temp_day['six_min'].tolist())
        temp_dic['AWND'] = ave_wind_speed_extractor(df_temp_day['wind'].tolist())
        temp_dic['SNOW'] = snow_amount_extractor(df_temp_day['description'].tolist(),df_temp_day['one_prec'].tolist())
        temp_dic['last_hour'] = int(last_hour)
        return temp_dic
def earliest_day_forecast():
    weather_forecast_url = 'https://forecast.weather.gov/MapClick.php?lat=42.3587&lon=-71.0567&unit=0&lg=english&FcstType=digital'
    req = requests.get(weather_forecast_url)
    req.raise_for_status()
    if req.status_code == requests.codes.ok:
        soup = BeautifulSoup(req.text, 'html.parser')
        table = soup.find_all('table')[7]
        rows = table.find_all('tr')
        list_list = []
        for row in rows:
            eles = row.find_all('td')
            eles = [ele.text for ele in eles]
            list_list.append(eles)
        del list_list[0]
        df_weather_forecast = pd.DataFrame(list_list)
        df_weather_forecast = df_weather_forecast.transpose()
        headers = df_weather_forecast.iloc[0]
        df_weather_forecast = df_weather_forecast[1:]
        df_weather_forecast.columns = headers
        df_weather_forecast['Hour (EDT)'] = df_weather_forecast['Hour (EDT)'].astype(int)
        min_ind = df_weather_forecast['Hour (EDT)'].idxmin()
        min_loc = df_weather_forecast.index.get_loc(min_ind)
        if min_loc == 0:
            df_weather_needed = df_weather_forecast
        else:
            df_weather_needed = df_weather_forecast[:min_loc]
        df_weather_needed = df_weather_needed[['Date', 'Hour (EDT)', 'Temperature (°F)', 'Surface Wind (mph)', 'Rain']]
        forecast_dic = {}
        forecast_dic['month'] = int(df_weather_needed.iat[0,df_weather_needed.columns.get_loc('Date')][:2])
        forecast_dic['day'] = int(df_weather_needed.iat[0,df_weather_needed.columns.get_loc('Date')][3:])
        forecast_dic['first_hour'] = df_weather_needed.iat[0,df_weather_needed.columns.get_loc('Hour (EDT)')]
        df_weather_needed['Temperature (°F)'] = df_weather_needed['Temperature (°F)'].astype(float)
        temperature_list = df_weather_needed['Temperature (°F)'].tolist()
        forecast_dic['TMAX'] = max(temperature_list)
        forecast_dic['TMIN'] = min(temperature_list)
        df_weather_needed['Surface Wind (mph)'] = df_weather_needed['Surface Wind (mph)'].astype(float)
        forecast_dic['AWND'] = df_weather_needed['Surface Wind (mph)'].mean()
        forecast_dic['PRCP'] = 0.0 #Need to figure out how to make it nonzero
        forecast_dic['SNOW'] = 0.0 #Need to figure out how to make it nonzero
        return forecast_dic
#Extract data from Fred and return a dataframe
def extract_fred_data(series_id = 'MAURN', api_key = '007198ec987cc488277fcc2b0984d47d', start_time = '2012-07-01'):
    url = 'https://api.stlouisfed.org/fred/series/observations?series_id=' + series_id + '&api_key=' + api_key + '&file_type=json' + '&observation_start=' + start_time
    req = requests.get(url)
    req.raise_for_status()
    if req.status_code == requests.codes.ok:
        data_json = json.loads(req.text)
        data_list = data_json['observations']
        df = pd.DataFrame(data_list)
        del df['realtime_start']
        del df['realtime_end']
        df.rename(columns = {'value':series_id},inplace = True)
        df['year'] = df['date'].apply(lambda x: int(x[:4]))
        df['month'] = df['date'].apply(lambda x: int(x[5:7]))
        del df['date']
        df['year'] = df.year.astype('category')
        df['month'] = df.month.astype('category')
        return df
def get_holiday(year, month, day):
    dt_obj = datetime.datetime(year, month, day)
    ma_holidays = holidays.CountryHoliday('US', prov=None, state='MA')
    hol_list = ["New Year's Day", 'Memorial Day', 'Independence Day', 'Labor Day', 'Thanksgiving', 'Christmas Day']
    if month == 12 and day >= 27 and day <= 30:
        return 'Holiday Season'
    holiday = ma_holidays.get(dt_obj)
    if holiday in hol_list:
        return str(holiday)
    dt_before_obj = dt_obj - datetime.timedelta(days=1)
    holiday = ma_holidays.get(dt_before_obj)
    if holiday in hol_list:
        return 'Post-' + str(holiday)
    dt_after_obj = dt_obj + datetime.timedelta(days=1)
    holiday = ma_holidays.get(dt_after_obj)
    if holiday in hol_list:
        return str(holiday) + ' Eve'
    return 'None'
def make_data(ser_id = 'MAURN', crime_list = ['AGGRAVATED ASSAULT','AUTO THEFT','COMMERCIAL BURGLARY','HOMICIDE','LARCENY','OTHER BURGLARY','RESIDENTIAL BURGLARY','ROBBERY']):
    ndw = newest_day_weather()
    edf = earliest_day_forecast()
    res = {}
    if ndw['day'] != edf['day']:#Only edf counts then
        res = edf
        res['SNOW'] = 0.0 #We haven't figured out how to get snow info from forecast data yet
    else:
        res['month'] = edf['month']
        res['day'] = edf['day']
        if ndw['TMAX'] is None:
            res['TMAX'] = edf['TMAX']
        else:
            res['TMAX'] = max(edf['TMAX'], ndw['TMAX'])
        if ndw['TMIN'] is None:
            res['TMIN'] = edf['TMIN']
        else:
            res['TMIN'] = min(edf['TMIN'], ndw['TMIN'])
        res['PRCP'] = edf['PRCP'] + ndw['PRCP']
        res['SNOW'] = edf['SNOW'] + ndw['SNOW']
        res['AWND'] = ((24 - edf['first_hour']) * edf['AWND'] + (1 + ndw['last_hour']) * ndw['AWND']) / 24
    #Temporarily get rid of SNOW and PRCP due to lack of data
    res.pop('SNOW',None)
    res.pop('PRCP',None)
    #Now process year and dayw
    now = datetime.datetime.now()
    local_month = now.month
    local_year = now.year
    if local_month == 1 and res['month'] == 12:#Need to move one day back
        res['year'] = local_year - 1
    elif local_month == 12 and res['month'] == 1:#Need to move one day forward
        res['year'] = local_year + 1
    else:
        res['year'] = local_year
    day = datetime.datetime(res['year'],res['month'],res['day'])
    res['dayw'] = calendar.day_name[day.weekday()]
    series_id = ser_id
    #Now process unemployment rate
    df_ue = extract_fred_data(series_id = series_id)
    series_id_index = df_ue.columns.get_loc(series_id)
    df_ue_temp = df_ue.sort_values(by = ['year', 'month'])
    size = df_ue_temp.shape[0]
    res[series_id] = float(df_ue_temp.iat[size - 1, series_id_index])
    #Now process holiday
    res['HOLIDAY'] = get_holiday(res['year'], res['month'], res['day'])
    #Time to convert everything to a dataframe
    df_res = pd.DataFrame(res, index = [0])
    df_res['year'] = df_res['year'].astype('category')
    df_res['month'] = df_res['month'].astype('category')
    df_res['day'] = df_res['day'].astype('category')
    df_res['dayw'] = df_res['dayw'].astype('category')
    df_res['HOLIDAY'] = df_res['HOLIDAY'].astype('category')
    #Expand according to crime
    short_col_list = df_res.columns
    df_final = pd.DataFrame(np.repeat(df_res.values, len(crime_list), axis = 0), columns = short_col_list)
    df_final['crime'] = pd.Series(1 * crime_list)
    #Time to get dummies
    col_list = ['AWND',
 'TMAX',
 'TMIN',
 ser_id,
 'crime_AGGRAVATED ASSAULT',
 'crime_AUTO THEFT',
 'crime_COMMERCIAL BURGLARY',
 'crime_HOMICIDE',
 'crime_LARCENY',
 'crime_OTHER BURGLARY',
 'crime_RESIDENTIAL BURGLARY',
 'crime_ROBBERY',
 'year_2012',
 'year_2013',
 'year_2014',
 'year_2015',
 'year_2016',
 'year_2017',
 'year_2018',
 'year_2019',
 'month_1',
 'month_2',
 'month_3',
 'month_4',
 'month_5',
 'month_6',
 'month_7',
 'month_8',
 'month_9',
 'month_10',
 'month_11',
 'month_12',
 'day_1',
 'day_2',
 'day_3',
 'day_4',
 'day_5',
 'day_6',
 'day_7',
 'day_8',
 'day_9',
 'day_10',
 'day_11',
 'day_12',
 'day_13',
 'day_14',
 'day_15',
 'day_16',
 'day_17',
 'day_18',
 'day_19',
 'day_20',
 'day_21',
 'day_22',
 'day_23',
 'day_24',
 'day_25',
 'day_26',
 'day_27',
 'day_28',
 'day_29',
 'day_30',
 'day_31',
 'dayw_Friday',
 'dayw_Monday',
 'dayw_Saturday',
 'dayw_Sunday',
 'dayw_Thursday',
 'dayw_Tuesday',
 'dayw_Wednesday',
 'HOLIDAY_Christmas Day',
 'HOLIDAY_Christmas Day Eve',
 'HOLIDAY_Holiday Season',
 'HOLIDAY_Independence Day',
 'HOLIDAY_Independence Day Eve',
 'HOLIDAY_Labor Day',
 'HOLIDAY_Labor Day Eve',
 'HOLIDAY_Memorial Day',
 'HOLIDAY_Memorial Day Eve',
 "HOLIDAY_New Year's Day",
 "HOLIDAY_New Year's Day Eve",
 'HOLIDAY_Post-Christmas Day',
 'HOLIDAY_Post-Independence Day',
 'HOLIDAY_Post-Labor Day',
 'HOLIDAY_Post-Memorial Day',
 "HOLIDAY_Post-New Year's Day",
 'HOLIDAY_Post-Thanksgiving',
 'HOLIDAY_Thanksgiving',
 'HOLIDAY_Thanksgiving Eve','HOLIDAY_None']
    df_final['TMAX'] = df_final['TMAX'].astype('float64')
    df_final['TMIN'] = df_final['TMIN'].astype('float64')
    #df_final['PRCP'] = df_final['PRCP'].astype('float64')
    #df_final['SNOW'] = df_final['SNOW'].astype('float64')
    df_final['AWND'] = df_final['AWND'].astype('float64')
    df_final[ser_id] = df_final[ser_id].astype('float64')
    df_final_dummies = pd.get_dummies(df_final)
    num_rows = df_final_dummies.shape[0]
    #print(df_final_dummies)
    for col in col_list:
        if col not in df_final_dummies.columns:
            df_final_dummies[col] = np.zeros(num_rows)
    df_final_dummies = df_final_dummies[col_list]    
    return df_final_dummies, datetime.datetime(res['year'], res['month'], res['day'])
def predict_today_crimes(crime_list = ['AGGRAVATED ASSAULT','AUTO THEFT','COMMERCIAL BURGLARY','HOMICIDE','LARCENY','OTHER BURGLARY','RESIDENTIAL BURGLARY','ROBBERY'], path = '/home/yingzhou474/mysite/'):
    final_X_df, date = make_data()
    final_X = final_X_df.values
    lgbm_final = pickle.load(open(path + 'lgbm_reg.p','rb'))
    scaler_final = pickle.load(open(path + 'lgbm_scaler.p','rb'))
    final_X_scaled = scaler_final.transform(final_X)
    final_y = lgbm_final.predict(final_X_scaled, num_iteration=lgbm_final.best_iteration_)
    crime_types = len(crime_list)
    prediction_dic = {}
    for i in range(crime_types):
        if final_y[i] < 0:#The amount of crimes should never be negative
            final_y[i] = 0.00
        prediction_dic[crime_list[i]] = round(final_y[i],2)
    return prediction_dic, date
if __name__ == '__main__':
    print(predict_today_crimes(path = '/Users/CatLover/Documents/DataScience/BostonCrime/production/'))
