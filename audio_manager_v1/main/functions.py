
import main.parameters as parameters
from main.parameters import *

import scipy



import sqlite3
from sqlite3 import Error
import requests

import json
from pathlib import Path
from tkinter import filedialog
from tkinter import *

import os
from scipy import signal

from scipy.signal import butter, lfilter, freqz
import numpy as np
from scipy.ndimage.filters import maximum_filter
from scipy.signal import butter, lfilter
# import pylab
import matplotlib.pyplot as plt
import librosa.display

import soundfile as sf

from subprocess import PIPE, run

from librosa import display, onset

from PIL import ImageTk,Image 

from datetime import datetime
import time
from pytz import timezone
from pytz import all_timezones

import tensorflow as tf


import zipfile
import random

from tensorflow.keras.optimizers import RMSprop
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.optimizers import Adam
from tensorflow.keras import regularizers

from shutil import copyfile

# from google.colab import files
from keras.preprocessing import image


# db_file = "/home/tim/Work/Cacophony/eclipse-workspace/audio_manager_v1/audio_analysis_db2.db"
conn = None

def get_database_connection():
    """ create a database connection to the SQLite database
        specified by the db_file
    :param db_file: database file
    :return: Connection object or None
    """

    # https://stackoverflow.com/questions/8587610/unboundlocalerror-local-variable-conn-referenced-before-assignment
    global conn
    if conn is None:
        try:
            conn = sqlite3.connect(db_file)           
        except Error as e:
            print(e)
  
    return conn       
    

def get_tags_from_server(device_id):
    print('about to get tags from server for device ', device_id)
    

def get_recordings_from_server(device_name, device_super_name):
    if not device_name:
        print('Device name can NOT be null')
        return
    
    if not device_super_name:
        print('Device Super name can NOT be null')
        return    
        
    print('About to get recordings from server')
    retrieve_available_recordings_from_server(device_name, device_super_name)
    
def get_recordings_from_server_for_all_devices():
    sql = '''select distinct device_name, device_super_name from recordings'''
    cur = get_database_connection().cursor()  
    cur.execute(sql) 
    rows = cur.fetchall() 
    for row in rows:
        device_name = row[0]
        device_super_name = row[1]
        retrieve_available_recordings_from_server(device_name, device_super_name)
          
def retrieve_missing_recording_information():
    sql = ''' SELECT recording_id from recordings where recordingDateTime IS NULL '''
    cur = get_database_connection().cursor()  
   
    cur.execute(sql) 
    
    rows = cur.fetchall() 
    numberOfRows = len(rows)
    count = 0
    for row in rows:
        recording_id =  row[0]
        print("Processing ", count, " of ", numberOfRows)
        print("About to get recording information for ", recording_id)
        update_recording_information_for_single_recording(recording_id)
        count += 1
        
        
        
    
def get_latest_recording_id_from_local_db(device_name, device_super_name):
    # Need the last recording ID for this device, that we already have   

#     https://docs.python.org/2/library/sqlite3.html
    sql = ''' SELECT audio_file_id FROM audio_files WHERE device_super_name = ? ORDER BY audio_file_id DESC LIMIT 1'''
    cur = get_database_connection().cursor()  
   
    cur.execute(sql,(device_super_name,))   
 
    rows = cur.fetchall() 
    for row in rows:
        return row[0]
    
def retrieve_available_recordings_from_server(device_name, device_super_name):      

    recordings_folder = getRecordingsFolder()     

    ids_of_recordings_to_download = get_recording_ids_for_device_name(device_name)
    
    # remove ids of recordings that we already have
    already_downloaded = []
    for file in os.listdir(recordings_folder):
        already_downloaded.append(os.path.splitext(file)[0])
       
    already_downloaded_set = set(already_downloaded)  
        
    ids_of_recordings_to_still_to_download = []
    
    for recording_id in ids_of_recordings_to_download:
        if not recording_id in already_downloaded_set:
            ids_of_recordings_to_still_to_download.append(recording_id)
        else:
            print('Already have recording ',recording_id, ' so will not download')
            # but still check to see if it is in database (some aren't if the database was locked)
            try: 
                cur = get_database_connection().cursor()
                cur.execute("SELECT ID FROM recordings WHERE recording_id = ?", (recording_id, ))
                records = cur.fetchone()             # https://stackoverflow.com/questions/2440147/how-to-check-the-existence-of-a-row-in-sqlite-with-python
                
                if records is None:
                    insert_recording_into_database(recording_id,recording_id + '.m4a' ,device_name,device_super_name)
                    # Also get recording information from server
                    update_recording_information_for_single_recording(recording_id)
                                
            except Exception as e:
                print(e, '\n')
            
       
    for recording_id in ids_of_recordings_to_still_to_download:
#         print('About to get token for downloading ',recording_id)
        token_for_retrieving_recording = get_token_for_retrieving_recording(recording_id)
        print('About to get recording ',recording_id)
        get_recording_from_server(token_for_retrieving_recording, recording_id, device_name, device_super_name)
        
        # Also get recording information from server
        update_recording_information_for_single_recording(recording_id)
     
    print('Finished retrieving recordings')  
#     print('Now going to retrieve tags')  
#     
#     # 19 Dec 2019 Decided not to get tags, but maybe later I'll put this on a separate button, as it could be useful to use tags that others have created.
# #     get_all_tags_for_all_devices_in_local_database() 
#     print('Finished retrieving tags') 
#     print('Finished all')  
        
def get_recording_from_server(token_for_retrieving_recording, recording_id, device_name, device_super_name):
    try:
      
        recording_local_filename = getRecordingsFolder() + '/' + recording_id + '.m4a'
            
        # Don't download it if we already have it.       
       
        if not os.path.exists(recording_local_filename):
            url = server_endpoint + get_a_recording
            querystring = {"jwt":token_for_retrieving_recording}     
           
            resp_for_getting_a_recording = requests.request("GET", url, params=querystring)
           
            if resp_for_getting_a_recording.status_code != 200:
                # This means something went wrong.
                print('Error from server is: ', resp_for_getting_a_recording.text)
                return               
             
            with open(recording_local_filename, 'wb') as f:  
                f.write(resp_for_getting_a_recording.content)
                
            # Update local database
            insert_recording_into_database(recording_id,recording_id + '.m4a' ,device_name,device_super_name)
            
        else:
            print('\t\tAlready have recording ', str(recording_id) , ' - so will not download again\n')
    except Exception as e:
        print(e, '\n')
        print('\t\tUnable to download recording ' + str(recording_id), '\n')
        
def get_token_for_retrieving_recording(recording_id):
    user_token = get_cacophony_user_token()

    get_a_token_for_recording_endpoint = server_endpoint + get_a_token_for_getting_a_recording_url + recording_id

    headers = {'Authorization': user_token}

    resp_for_getting_a_recordingToken = requests.request("GET", get_a_token_for_recording_endpoint, headers=headers)
    if resp_for_getting_a_recordingToken.status_code != 200:
        sys.exit('Could not get download token - exiting')
    recording_data = resp_for_getting_a_recordingToken.json()
    recording_download_token = recording_data['downloadFileJWT']
    
    return recording_download_token
    
def get_recording_ids_for_device_name(device_name): 
    
    # Get the highest recording id for this device that has already been downloaded
    cur = get_database_connection().cursor()   
    cur.execute("SELECT MAX(recording_id) FROM recordings WHERE device_name = ?", (device_name,))
    rows = cur.fetchall() 
    current_max_recording_id_for_this_device = rows[0][0]
    if current_max_recording_id_for_this_device is None:
        current_max_recording_id_for_this_device = 0
    current_max_recording_id_for_this_device = 0
        
    print('device_name ', device_name)
    print('max_recording_id ', current_max_recording_id_for_this_device)
    
    device_id = get_device_id_using_device_name(device_name)
    print('device_id is ', device_id)
    ids_recordings_for_device_name = []
    offset = 0
    while True:
        ids_of_recordings_to_download= get_ids_of_recordings_to_download_using_deviceId(device_id,offset, current_max_recording_id_for_this_device)
        print('ids_of_recordings_to_download ', ids_of_recordings_to_download)
        ids_recordings_for_device_name += ids_of_recordings_to_download
        
        # Check to see if the list from the server contains the previous max recording_id.  If it does, then don't get anymore ids
        
        if (len(ids_of_recordings_to_download) > 0):
            offset+=300
        else:
            break
    return ids_recordings_for_device_name

def get_ids_of_recordings_to_download_using_deviceId(deviceId, offset, current_max_recording_id):
    # This will get a list of the recording ids for every recording of length 59,60,61,62 from device_name
    user_token = get_cacophony_user_token()
   
    url = server_endpoint + query_available_recordings
    
    where_param = {}
    where_param['DeviceId'] = deviceId
    where_param['duration'] = 59,60,61,62
    
    grt_id_param = {}
    grt_id_param['$gt'] = current_max_recording_id
    where_param['id'] = grt_id_param
    
    json_where_param = json.dumps(where_param) 

    querystring = {"offset":offset, "where":json_where_param}    
    
    headers = {'Authorization': user_token}  

    resp = requests.request("GET", url, headers=headers, params=querystring)
   
    if resp.status_code != 200:
        # This means something went wrong.
        print('Error from server is: ', resp.text)
        sys.exit('Could not download file - exiting')            
    
    data = resp.json() 
    
    recordings = data['rows'] 
    
    print('Number of recordings is ', len(recordings))

    ids_of_recordings_to_download = []    
    for recording in recordings:        
        recording_id = str(recording['id'])
        ids_of_recordings_to_download.append(recording_id)
        
    return ids_of_recordings_to_download    

def get_device_id_using_device_name(device_name):
    user_token = get_cacophony_user_token()
    url = server_endpoint + devices_endpoint
      
    headers = {'Authorization': user_token}  

    resp = requests.request("GET", url, headers=headers)
   
    if resp.status_code != 200:
        # This means something went wrong.
        print('Error from server is: ', resp.text)
        sys.exit('Could not download file - exiting')
    
    data = resp.json()

    devices = data['devices'] 
    rows = devices['rows']
    for row in rows:
        devicename = row['devicename']        
        if devicename == device_name:
                device_id = row['id']
                return device_id     
            
def get_cacophony_user_token():
    global cacophony_user_token
    global cacophony_user_name
    global cacophony_user_password 
    if cacophony_user_token:
        return cacophony_user_token
    
    print('About to get user_token from server')
    username = cacophony_user_name
    if cacophony_user_password == '':
        cacophony_user_password = input("Enter password for Cacophony user " + username + " (or change cacophony_user_name in parameters file): ")
           
    requestBody = {"nameOrEmail": username, "password": cacophony_user_password }
    login_endpoint = server_endpoint + login_user_url
    resp = requests.post(login_endpoint, data=requestBody)
    if resp.status_code != 200:
        # This means something went wrong.
        sys.exit('Could not connect to Cacophony Server - exiting')
    
    data = resp.json()
    cacophony_user_token = data['token']
    return cacophony_user_token
    
def load_recordings_from_local_folder(device_name, device_super_name):
    
    input_folder = filedialog.askdirectory()

    recordings_folder = getRecordingsFolder()
    
    for filename in os.listdir( input_folder):
        recording_id = filename.replace('-','.').split('.')[0]
        filename2 = recording_id +'.m4a'

        insert_recording_into_database(recording_id,filename2,device_name,device_super_name)
        
        # Now move file to recordings folder
        audio_in_path = input_folder + '/' + filename       
        audio_out_path = recordings_folder + '/' + filename2
        
        print('Moving ', filename, ' to ', audio_out_path)
        os.rename(audio_in_path, audio_out_path)

        # Now need to get information about this recording from server
        update_recording_information_for_single_recording(recording_id)
        
def insert_recording_into_database(recording_id,filename,device_name,device_super_name):
    try:
        sql = ''' INSERT INTO recordings(recording_id,filename,device_name,device_super_name)
                  VALUES(?,?,?,?) '''
        cur = get_database_connection().cursor()
        cur.execute(sql, (recording_id,filename,device_name,device_super_name))
       
        get_database_connection().commit()
    except Exception as e:
        print(e, '\n')
        print('\t\tUnable to insert recording ' + str(recording_id), '\n')
        

def update_recordings_folder(recordings_folder):
    print("new_recording_folder ", recordings_folder)
    """
    update priority, begin_date, and end date of a task
    :param conn:
    :param recordings_folder:
    :return: project id
    """
    sql = ''' UPDATE settings
              SET downloaded_recordings_folder = ?               
              WHERE ID = 1'''
    cur = get_database_connection().cursor()
    cur.execute(sql, (recordings_folder,))
    get_database_connection().commit()      
        
def getRecordingsFolder():

    cur = get_database_connection().cursor()
    cur.execute("select * from settings")
 
    rows = cur.fetchall()
    home = str(Path.home())
    print('home ', home)
 
    for row in rows:       
        return  home + '/' + row[0] 
    
    
def getRecordingsFolderWithOutHome():
    cur = get_database_connection().cursor()
    cur.execute("select * from settings")
 
    rows = cur.fetchall()   
 
    for row in rows:     
        return row[0]     
        
def update_recording_information_for_single_recording(recording_id):
    print('About to update recording information for recording ', recording_id)    
    recording_information = get_recording_information_for_a_single_recording(recording_id)
    print('recording_information ', recording_information)    
    if recording_information == None:        
        print('recording_information == None')     
        return
         
    recording = recording_information['recording']    
    recordingDateTime = recording['recordingDateTime']    
    recordingDateTimeNZ = convert_time_zones(recordingDateTime)
    relativeToDawn = recording['relativeToDawn']    
    relativeToDusk = recording['relativeToDusk']    
    duration = recording['duration'] 
       
    location = recording['location']        
    coordinates = location['coordinates']    
    locationLat = coordinates[0]    
    locationLong = coordinates[1]  
       
    version = recording['version']    
    batteryLevel = recording['batteryLevel']    
    
    additionalMetadata = recording['additionalMetadata']    
    phoneModel = additionalMetadata['Phone model']    
    androidApiLevel = additionalMetadata['Android API Level']  
    
    Device = recording['Device']    
    deviceId = Device['id']
    device_name = Device['devicename']
         
    nightRecording =  'false'
    
    if relativeToDusk is not None:
        if relativeToDusk > 0:
            nightRecording = 'true' 
    elif relativeToDawn is not None:
        if relativeToDawn < 0:
            nightRecording = 'true'   
                   
#     update_recording_in_database(recordingDateTime, relativeToDawn, relativeToDusk, duration, locationLat, locationLong, version, batteryLevel, phoneModel, androidApiLevel, deviceId, nightRecording, device_name, recording_id, recordingDateTimeNZ)
    update_recording_in_database(recordingDateTime, relativeToDawn, relativeToDusk, duration, locationLat, locationLong, version, batteryLevel, phoneModel, androidApiLevel, deviceId, nightRecording, device_name, recording_id, recordingDateTimeNZ)
    print('Finished updating recording information for recording ', recording_id)
               
  
def update_recording_in_database(recordingDateTime, relativeToDawn, relativeToDusk, duration, locationLat, locationLong, version, batteryLevel, phoneModel,androidApiLevel, deviceId, nightRecording, device_name, recording_id, recordingDateTimeNZ):
    try:
#         conn = get_database_connection()
        # https://www.sqlitetutorial.net/sqlite-python/update/
        sql = ''' UPDATE recordings 
                  SET recordingDateTime = ?,
                      relativeToDawn = ?,
                      relativeToDusk = ?,
                      duration = ?,
                      locationLat = ?,
                      locationLong = ?,
                      version = ?,
                      batteryLevel = ?,
                      phoneModel = ?,
                      androidApiLevel = ?,
                      deviceId = ?,
                      nightRecording = ?,
                      device_name = ?,
                      recordingDateTimeNZ = ?
                  WHERE recording_id = ? '''
        cur = get_database_connection().cursor()
        cur.execute(sql, (recordingDateTime, relativeToDawn, relativeToDusk, duration, locationLat, locationLong, version, batteryLevel, phoneModel, androidApiLevel, deviceId, nightRecording, device_name, recordingDateTimeNZ, recording_id))
        get_database_connection().commit()
    except Exception as e:
        print(e, '\n')
        print('\t\tUnable to insert recording ' + str(recording_id), '\n')
        
   
    
def get_recording_information_for_a_single_recording(recording_id):
    user_token = get_cacophony_user_token()

    get_a_token_for_recording_endpoint = server_endpoint + get_information_on_single_recording + recording_id

    headers = {'Authorization': user_token}

    resp_for_getting_a_recordingToken = requests.request("GET", get_a_token_for_recording_endpoint, headers=headers)
    if resp_for_getting_a_recordingToken.status_code != 200:
        print('Could not get download token')
        return None
    recording_data_for_single_recording = resp_for_getting_a_recordingToken.json()      
    
    return recording_data_for_single_recording     



def update_recording_information_for_all_local_database_recordings():
    cur = get_database_connection().cursor()
    cur.execute("SELECT recording_id, recordingDateTime FROM recordings")
 
    rows = cur.fetchall()
 
    for row in rows:
        # Don't update if we already have recordingDateTime
        recordingDateTime = row[1]
        if not recordingDateTime:
            print(recordingDateTime, ' is empty so will update record')
            recording_id = row[0]
            update_recording_information_for_single_recording(recording_id)
        print('Finished updating recording information')
    


def get_audio_recordings_with_tags_information_from_server(user_token, recording_type, deviceId):
    print('Retrieving recordings basic information from Cacophony Server\n')
    url = server_endpoint + query_available_recordings
    
    where_param = {}
    where_param['type'] = recording_type    
    where_param['DeviceId'] = deviceId
    json_where_param = json.dumps(where_param)
    querystring = {"tagMode":"tagged", "where":json_where_param}    
    headers = {'Authorization': user_token}  

    resp = requests.request("GET", url, headers=headers, params=querystring)
   
    if resp.status_code != 200:
        # This means something went wrong.
        print('Error from server is: ', resp.text)
        sys.exit('Could not download file - exiting')    
        
    
    data = resp.json()
   
    recordings = data['rows']
    
    return recordings   



def get_and_store_tag_information_for_recording(recording_id, deviceId, device_name, device_super_name):
    single_recording_full_information = get_recording_information_for_a_single_recording(recording_id)
    recording = single_recording_full_information['recording']  
    tags = recording['Tags']   
    for tag in tags:
        server_Id = tag['id']
        what = tag['what']
        detail = tag['detail']
        confidence = tag['confidence']
        startTime = tag['startTime']
        duration = tag['duration']
        automatic = tag['automatic']
        version = tag['version']
        createdAt = tag['createdAt']
        tagger =tag['tagger']        
        tagger_username = tagger['username']
        what = tag['what']
        insert_tag_into_database(recording_id,server_Id, what, detail, confidence, startTime, duration, automatic, version, createdAt, tagger_username, deviceId, device_name, device_super_name)
    
    

    
def insert_tag_into_database(recording_id,server_Id, what, detail, confidence, startTime, duration, automatic, version, createdAt, tagger_username, deviceId, device_name, device_super_name ):
    # Use this for tags that have been downloaded from the server
    try:
        if check_if_tag_alredy_in_database(server_Id) == True:
            print('tag exists')
            return
        else:
            print('going to insert tag')

        sql = ''' INSERT INTO tags(recording_id,server_Id, what, detail, confidence, startTime, duration, automatic, version, createdAt, tagger_username, deviceId, device_name, device_super_name)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) '''
        cur = get_database_connection().cursor()
        cur.execute(sql, (recording_id,server_Id, what, detail, confidence, startTime, duration, automatic, version, createdAt, tagger_username, deviceId, device_name, device_super_name))
        get_database_connection().commit()
    except Exception as e:
        print(e, '\n')
        print('\t\tUnable to insert tag ' + str(recording_id), '\n')   
        
def insert_locally_created_tag_into_database(recording_id,what, detail, confidence, startTime, duration, createdAt, tagger_username, deviceId, device_name, device_super_name ):
    # Use this is the tag was created in this application, rather than being downloaded from the server - becuase some fields are missing e.g. server_Id
    try:        

        sql = ''' INSERT INTO tags(recording_id, what, detail, confidence, startTime, duration, createdAt, tagger_username, deviceId, device_name, device_super_name)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?) '''
        cur = get_database_connection().cursor()
        cur.execute(sql, (recording_id, what, detail, confidence, startTime, duration, createdAt, tagger_username, deviceId, device_name, device_super_name))
        get_database_connection().commit()
    except Exception as e:
        print(e, '\n')
        print('\t\tUnable to insert tag ' + str(recording_id), '\n')   
       

def check_if_tag_alredy_in_database(server_Id):
    cur = get_database_connection().cursor()
    cur.execute("SELECT server_Id FROM tags WHERE server_Id = ?", (server_Id,))
    data=cur.fetchone()
    if data is None:
        return False
    else:
        return True


 
def get_all_tags_for_all_devices_in_local_database():
    user_token = get_cacophony_user_token()
    unique_devices = get_unique_devices_stored_locally()

    for unique_device in unique_devices:  
        deviceId = unique_device[0]
        device_name = unique_device[1]
        device_super_name = unique_device[2]        
      
        recording_type = 'audio'
        recordings_with_tags = get_audio_recordings_with_tags_information_from_server(user_token, recording_type, deviceId)

        for recording_with_tag in recordings_with_tags:
            print('device is', deviceId, '\n') 
            recording_id =recording_with_tag['id']
            print('recording_id ', recording_id, '\n')
            get_and_store_tag_information_for_recording(str(recording_id), deviceId, device_name, device_super_name)
    print('Finished getting tags from server')
            
    
     
def get_unique_devices_stored_locally():
    cur = get_database_connection().cursor()
    cur.execute("SELECT DISTINCT deviceId, device_name, device_super_name FROM recordings") 
    rows = cur.fetchall()
    return rows   

def get_unique_recording_ids_that_have_been_tagged_with_this_tag_stored_locally(tag):
    print('tag', tag)
    cur = get_database_connection().cursor()
    cur.execute("SELECT DISTINCT recording_id FROM tags WHERE what = ?", (tag,)) 
    rows = cur.fetchall()
    return rows 


        
def get_onsets_stored_locally(onset_version):
    global version
    if onset_version:
        version_to_use = onset_version
    else:
        version_to_use = version
        
    cur = get_database_connection().cursor()
    cur.execute("SELECT version, recording_id, start_time_seconds, duration_seconds FROM onsets WHERE version = ? ORDER BY recording_id", (version_to_use)) 
    rows = cur.fetchall()
    return rows 

# def get_onsets_stored_locally_for_recording_id(onset_version, recording_id):
#     global version
#     if onset_version:
#         version_to_use = onset_version
#     else:
#         version_to_use = version
#         
#     cur = get_database_connection().cursor()
#     cur.execute("SELECT version, recording_id, start_time_seconds, duration_seconds FROM onsets WHERE version = ? AND recording_id = ? ORDER BY recording_id", (version_to_use, recording_id)) 
#     rows = cur.fetchall()
#     return rows

def get_onsets_stored_locally_for_recording_id(version_to_use, recording_id):
#     global version
    cur = get_database_connection().cursor()
    if version_to_use:
#         version_to_use = onset_version
        cur.execute("SELECT version, recording_id, start_time_seconds, duration_seconds FROM onsets WHERE version = ? AND recording_id = ? ORDER BY recording_id", (version_to_use, recording_id)) 
    else: 
        cur.execute("SELECT version, recording_id, start_time_seconds, duration_seconds FROM onsets WHERE recording_id = ? ORDER BY recording_id", (recording_id,))
    rows = cur.fetchall()
    return rows

def get_model_run_results(modelRunName, actualConfirmedFilter, predictedFilter, predicted_probability_filter, predicted_probability_filter_value_str, location_filter, actual_confirmed_other, predicted_other, used_to_create_model_filter, recording_id_filter_value):   
       
    if location_filter =='Not Used':
        location_filter ='not_used'
         
    sqlBuilding = "SELECT ID FROM model_run_result WHERE modelRunName = '" + modelRunName + "'"
    
    if actualConfirmedFilter !='not_used':
        sqlBuilding += " AND "
        if actualConfirmedFilter == "IS NULL":
            if actual_confirmed_other == 'off':
                sqlBuilding += "actual_confirmed IS NULL"
            else: # Everything other is checked
                sqlBuilding += "actual_confirmed IS NOT NULL"
        else:
            if actual_confirmed_other == 'off':
                sqlBuilding +=  "actual_confirmed = '" + actualConfirmedFilter + "'"
            else: # Everything other is checked
                sqlBuilding +=  "actual_confirmed <> '" + actualConfirmedFilter + "'"
                
            
    if predictedFilter !='not_used':
        sqlBuilding += " AND "
        if predictedFilter == "IS NULL":
            if predicted_other == 'off':
                sqlBuilding += "predictedByModel IS NULL"
            else:
                sqlBuilding += "predictedByModel IS NOT NULL"
        else:
            if predicted_other == 'off':
                sqlBuilding +=  "predictedByModel = '" + predictedFilter + "'"
            else:
                sqlBuilding +=  "predictedByModel <> '" + predictedFilter + "'"
            
    if location_filter !='not_used':
        sqlBuilding += " AND "
        sqlBuilding +=  "device_super_name = '" + location_filter + "'"
        
    if (predicted_probability_filter_value_str == '') or (predicted_probability_filter == 'not_used'):
        predicted_probability_filter = 'not_used'
    else:    
        if predicted_probability_filter == 'greater_than':  
            probabilty_comparator = '>'
#             predicted_probability_filter_value = float(predicted_probability_filter_value_str)    
        elif predicted_probability_filter == 'less_than': 
            probabilty_comparator = '<'
#             predicted_probability_filter_value = float(predicted_probability_filter_value_str)    
        sqlBuilding += " AND "
#         sqlBuilding += " probability " + probabilty_comparator + " '" + predicted_probability_filter_value + "'"
        sqlBuilding += " probability " + probabilty_comparator + " '" + predicted_probability_filter_value_str + "'"
        
    if used_to_create_model_filter != 'not_used':
        sqlBuilding += " AND "
        if used_to_create_model_filter == 'yes':
            sqlBuilding +=  "used_to_create_model = 1"
        else:
#             sqlBuilding +=  "used_to_create_model = 0"
            sqlBuilding +=  "used_to_create_model IS NULL"
            
    if recording_id_filter_value:
        sqlBuilding += " AND "        
        sqlBuilding +=  "recording_id = '" + recording_id_filter_value + "'"
        
        
    sqlBuilding += " ORDER BY recording_id DESC, startTime ASC"
        
    print("The sql is: ", sqlBuilding)
    cur = get_database_connection().cursor()
    cur.execute(sqlBuilding)
#     cur.execute("SELECT ID FROM model_run_result WHERE modelRunName = '2019_12_11_1' ORDER BY recording_id DESC, startTime ASC")
    rows = cur.fetchall()
    return rows

def get_model_run_result(database_ID):        
    cur = get_database_connection().cursor()
    cur.execute("SELECT ID, recording_id, startTime, duration, actual, predictedByModel, actual_confirmed, probability, device_super_name FROM model_run_result WHERE ID = ?", (database_ID,)) 
    rows = cur.fetchall()
    return rows[0] 
    
def scan_local_folder_for_recordings_not_in_local_db_and_update(device_name, device_super_name):
    recordings_folder = getRecordingsFolder()
    for filename in os.listdir(recordings_folder):
        recording_id = filename.replace('-','.').split('.')[0]
        print(recording_id)
        cur = get_database_connection().cursor()
        cur.execute("SELECT * FROM recordings WHERE recording_id = ?",(recording_id,))
        
        # https://stackoverflow.com/questions/16561362/python-how-to-check-if-a-result-set-is-empty
        row = cur.fetchone()
        if row == None:
            # Get the information for this recording from server and insert into local db   
            filename = recording_id + '.m4a'
            insert_recording_into_database(recording_id,filename, device_name,device_super_name) # The device name will be updated next when getting infor from server
            # Now update this recording with information from server
            update_recording_information_for_single_recording(recording_id)
           


    
def update_local_tags_with_version():
    # This is probably only used the once to modify intial rows to indicate they are from my first morepork tagging of Hammond Park
    cur = get_database_connection().cursor()
    cur.execute("select ID from tags")
 
    rows = cur.fetchall()     
 
    for row in rows:              
        ID =  row[0] 
        print('ID ', ID) 
        sql = ''' UPDATE tags
                  SET version = ?               
                  WHERE ID = ?'''
        cur = get_database_connection().cursor()
        cur.execute(sql, ('morepork_base', ID))
    
    get_database_connection().commit()    
    
def update_model_run_result(ID, actual_confirmed):
    cur = get_database_connection().cursor()
    sql = ''' UPDATE model_run_result
              SET actual_confirmed = ?               
              WHERE ID = ?'''
    if (actual_confirmed == 'None') or (actual_confirmed == 'not_used'): # Must not put None into the db as the model breaks - instead convert to Null as descrived here - https://johnmludwig.blogspot.com/2018/01/null-vs-none-in-sqlite3-for-python.html
        cur.execute(sql, (None, ID))
    else:
        cur.execute(sql, (actual_confirmed, ID))
    
    get_database_connection().commit()    
    
def update_onset(recording_id, start_time_seconds, actual_confirmed):
    cur = get_database_connection().cursor()
    if (actual_confirmed == 'None') or (actual_confirmed == 'not_used'): # Must not put None into the db as the model breaks - instead convert to Null as descrived here - https://johnmludwig.blogspot.com/2018/01/null-vs-none-in-sqlite3-for-python.html
        cur.execute("UPDATE onsets SET actual_confirmed = ? WHERE recording_id = ? AND start_time_seconds = ?", (None, recording_id, start_time_seconds))   
    else:        
        cur.execute("UPDATE onsets SET actual_confirmed = ? WHERE recording_id = ? AND start_time_seconds = ?", (actual_confirmed, recording_id, start_time_seconds))  
        
    get_database_connection().commit()      
  
def run_model(model_folder):
    # https://stackoverflow.com/questions/21406887/subprocess-changing-directory
    # https://stackoverflow.com/questions/1996518/retrieving-the-output-of-subprocess-call

    os.chdir(model_folder)  
    command = ['java', '--add-opens=java.base/java.lang=ALL-UNNAMED', '-jar', 'run.jar', 'shell=True']     
    
    result = run(command, stdout=PIPE, stderr=PIPE, text=True)   
    
    return result

    
def classify_onsets_using_weka_model():

    model_folder = base_folder + '/' + run_folder + '/' + weka_model_folder
    
    # Need to check if run.jar is there, otherwise run.jar will break later on
    weka_run_jar_filename_path = model_folder + '/' + weka_run_jar_filename        
    if not os.path.isfile(weka_run_jar_filename_path):
        print(weka_run_jar_filename, " is missing") 
        return 
    

    
    # Need to check model file is there, otherwise run.jar will break later on
    weka_model_filename_path = model_folder + '/' + weka_model_filename        
    if not os.path.isfile(weka_model_filename_path):
        print(weka_model_filename_path, " is missing") 
        return    

# As it takes about 24 hours to process all the onsets, I've split processing in to two stages - 
# first it does all the onsets that already have an actual_confirmed entry - 
# this might only take a minute or two as there are very few of them
# then it does the rest.  It is now OK to stop this process before it has finished as I'll probably never look at all the predictions - unless going to create tags on the server

    cur = get_database_connection().cursor()
    cur.execute("SELECT recording_id, start_time_seconds, duration_seconds, actual_confirmed, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ FROM onsets WHERE actual_confirmed IS NOT NULL ORDER BY recording_id DESC")
    
    onsetsWithActualConfirmed = cur.fetchall()  
    number_of_onsets = len(onsetsWithActualConfirmed)
    count = 0
    print('Processing onsets with actual_confirmed entry')
    for onsetWithActualConfirmed in onsetsWithActualConfirmed:
        count += 1        
        print('Processing onset', count, ' of ', number_of_onsets)
        classify_onsets_using_weka_model_helper(onsetWithActualConfirmed, model_folder)
    
    cur2 = get_database_connection().cursor()
    cur2.execute("SELECT recording_id, start_time_seconds, duration_seconds, actual_confirmed, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ FROM onsets WHERE actual_confirmed IS NULL ORDER BY recording_id DESC")
    onsetsWithNoActualConfirmed = cur2.fetchall()  
    number_of_onsets = len(onsetsWithNoActualConfirmed)
    count = 0
    print('Processing onsets with NO actual_confirmed entry')
    for onsetWithNoActualConfirmed in onsetsWithNoActualConfirmed:
        count += 1        
        print('Processing onset', count, ' of ', number_of_onsets)
        classify_onsets_using_weka_model_helper(onsetWithNoActualConfirmed, model_folder)   
        
def update_onsets_with_edge_histogram_features():  
    model_folder = base_folder + '/' + run_folder + '/' + weka_model_folder
    
    # Need to check if run.jar is there, otherwise run.jar will break later on
    get_edge_histogram_jar_filename_path = model_folder + '/' + get_edge_histogram_jar_filename        
    if not os.path.isfile(get_edge_histogram_jar_filename_path):
        print(get_edge_histogram_jar_filename_path, " is missing") 
        return 
        
    # Need to check model file is there, otherwise run.jar will break later on
    weka_model_filename_path = model_folder + '/' + weka_model_filename        
    if not os.path.isfile(weka_model_filename_path):
        print(weka_model_filename_path, " is missing") 
        return  
    
    cur = get_database_connection().cursor()
#     cur.execute("SELECT ID, recording_id, start_time_seconds, duration_seconds  FROM onsets WHERE MPEG7_Edge_Histogram0 IS NULL ORDER BY recording_id DESC")
    cur.execute("SELECT ID, recording_id, start_time_seconds, duration_seconds FROM onsets WHERE recording_id >= ? AND recording_id <= ? AND VERSION = 7 AND MPEG7_Edge_Histogram0 IS NULL ORDER BY recording_id DESC", (first_test_data_recording_id, last_test_data_recording_id))
#     cur.execute("SELECT ID, recording_id, start_time_seconds, duration_seconds  FROM onsets WHERE MPEG7_Edge_Histogram0 IS NULL AND device_super_name = 'chow' ORDER BY recording_id DESC")

   
    onsetsWithNoEdgeHistogramData = cur.fetchall()  
    number_of_onsets = len(onsetsWithNoEdgeHistogramData)
    count = 0
    print('Processing onsets with with No EdgeHistogram Data')
    previous_recording_id = -1
    y = None
    sr = None
    for onsetWithNoEdgeHistogramData in onsetsWithNoEdgeHistogramData:
        count += 1        
        
        ID = onsetWithNoEdgeHistogramData[0]
        recording_id = onsetWithNoEdgeHistogramData[1]
        
        if recording_id != previous_recording_id:
            print("recording_id changed from ", previous_recording_id, " to ", recording_id)
            y, sr = get_recording_array(recording_id)
            
        
        start_time_seconds = onsetWithNoEdgeHistogramData[2]
        duration_seconds = onsetWithNoEdgeHistogramData[3]  
        
        print('Processing onset', count, ' of ', number_of_onsets)
        create_single_focused_mel_spectrogram_for_model_input(recording_id, start_time_seconds, duration_seconds, y, sr)
                
        os.chdir(model_folder)  
        command = ['java', '--add-opens=java.base/java.lang=ALL-UNNAMED', '-jar', 'getEdgeHistogramFeatures.jar', 'shell=True']     
    
        result = run(command, stdout=PIPE, stderr=PIPE, text=True)   
        if result.returncode == 0:
#             print(result.stdout)
          
            result_stdout = result.stdout
            result_stdout_parts = result_stdout.split(',')
#             print('length', len(result_stdout_parts))
#             print('result_stdout_parts', result_stdout_parts)
            sql = '''UPDATE onsets
                SET MPEG7_Edge_Histogram0 = ?, 
                MPEG7_Edge_Histogram1 = ?,
                MPEG7_Edge_Histogram2 = ?,
                MPEG7_Edge_Histogram3 = ?,
                MPEG7_Edge_Histogram4 = ?,
                MPEG7_Edge_Histogram5 = ?,
                MPEG7_Edge_Histogram6 = ?,
                MPEG7_Edge_Histogram7 = ?,
                MPEG7_Edge_Histogram8 = ?,
                MPEG7_Edge_Histogram9 = ?,
                
                MPEG7_Edge_Histogram10 = ?, 
                MPEG7_Edge_Histogram11 = ?,
                MPEG7_Edge_Histogram12 = ?,
                MPEG7_Edge_Histogram13 = ?,
                MPEG7_Edge_Histogram14 = ?,
                MPEG7_Edge_Histogram15 = ?,
                MPEG7_Edge_Histogram16 = ?,
                MPEG7_Edge_Histogram17 = ?,
                MPEG7_Edge_Histogram18 = ?,
                MPEG7_Edge_Histogram19 = ?,
                
                MPEG7_Edge_Histogram20 = ?,
                MPEG7_Edge_Histogram21 = ?,
                MPEG7_Edge_Histogram22 = ?,
                MPEG7_Edge_Histogram23 = ?,
                MPEG7_Edge_Histogram24 = ?,
                MPEG7_Edge_Histogram25 = ?,
                MPEG7_Edge_Histogram26 = ?,
                MPEG7_Edge_Histogram27 = ?,
                MPEG7_Edge_Histogram28 = ?,
                MPEG7_Edge_Histogram29 = ?,
                
                MPEG7_Edge_Histogram30 = ?,
                MPEG7_Edge_Histogram31 = ?,
                MPEG7_Edge_Histogram32 = ?,
                MPEG7_Edge_Histogram33 = ?,
                MPEG7_Edge_Histogram34 = ?,
                MPEG7_Edge_Histogram35 = ?,
                MPEG7_Edge_Histogram36 = ?,
                MPEG7_Edge_Histogram37 = ?,
                MPEG7_Edge_Histogram38 = ?,
                MPEG7_Edge_Histogram39 = ?,
                
                MPEG7_Edge_Histogram40 = ?, 
                MPEG7_Edge_Histogram41 = ?,
                MPEG7_Edge_Histogram42 = ?,
                MPEG7_Edge_Histogram43 = ?,
                MPEG7_Edge_Histogram44 = ?,
                MPEG7_Edge_Histogram45 = ?,
                MPEG7_Edge_Histogram46 = ?,
                MPEG7_Edge_Histogram47 = ?,
                MPEG7_Edge_Histogram48 = ?,
                MPEG7_Edge_Histogram49 = ?,
                
                MPEG7_Edge_Histogram50 = ?, 
                MPEG7_Edge_Histogram51 = ?,
                MPEG7_Edge_Histogram52 = ?,
                MPEG7_Edge_Histogram53 = ?,
                MPEG7_Edge_Histogram54 = ?,
                MPEG7_Edge_Histogram55 = ?,
                MPEG7_Edge_Histogram56 = ?,
                MPEG7_Edge_Histogram57 = ?,
                MPEG7_Edge_Histogram58 = ?,
                MPEG7_Edge_Histogram59 = ?,
                
                MPEG7_Edge_Histogram60 = ?,
                MPEG7_Edge_Histogram61 = ?,
                MPEG7_Edge_Histogram62 = ?,
                MPEG7_Edge_Histogram63 = ?,
                MPEG7_Edge_Histogram64 = ?,
                MPEG7_Edge_Histogram65 = ?,
                MPEG7_Edge_Histogram66 = ?,
                MPEG7_Edge_Histogram67 = ?,
                MPEG7_Edge_Histogram68 = ?,
                MPEG7_Edge_Histogram69 = ?,
                
                MPEG7_Edge_Histogram70 = ?,
                MPEG7_Edge_Histogram71 = ?,
                MPEG7_Edge_Histogram72 = ?,
                MPEG7_Edge_Histogram73 = ?,
                MPEG7_Edge_Histogram74 = ?,
                MPEG7_Edge_Histogram75 = ?,
                MPEG7_Edge_Histogram76 = ?,
                MPEG7_Edge_Histogram77 = ?,
                MPEG7_Edge_Histogram78 = ?,
                MPEG7_Edge_Histogram79 = ?          
                                                           
                WHERE ID = ?'''
            
#             print('sql ', sql)           
        
            cur.execute(sql, (result_stdout_parts[1],
                              result_stdout_parts[2], 
                              result_stdout_parts[3], 
                              result_stdout_parts[4], 
                              result_stdout_parts[4], 
                              result_stdout_parts[6], 
                              result_stdout_parts[7], 
                              result_stdout_parts[8], 
                              result_stdout_parts[9],
                              
                              result_stdout_parts[10], 
                              result_stdout_parts[11],                             
                              result_stdout_parts[12], 
                              result_stdout_parts[13], 
                              result_stdout_parts[14], 
                              result_stdout_parts[14], 
                              result_stdout_parts[16], 
                              result_stdout_parts[17], 
                              result_stdout_parts[18], 
                              result_stdout_parts[19],
                              
                              result_stdout_parts[20],                              
                              result_stdout_parts[21],
                              result_stdout_parts[22], 
                              result_stdout_parts[23], 
                              result_stdout_parts[24], 
                              result_stdout_parts[24], 
                              result_stdout_parts[26], 
                              result_stdout_parts[27], 
                              result_stdout_parts[28], 
                              result_stdout_parts[29],
                              
                              result_stdout_parts[30],                              
                              result_stdout_parts[31],
                              result_stdout_parts[32], 
                              result_stdout_parts[33], 
                              result_stdout_parts[34], 
                              result_stdout_parts[34], 
                              result_stdout_parts[36], 
                              result_stdout_parts[37], 
                              result_stdout_parts[38], 
                              result_stdout_parts[39],
                              
                              result_stdout_parts[40],                              
                              result_stdout_parts[41],
                              result_stdout_parts[42], 
                              result_stdout_parts[43], 
                              result_stdout_parts[44], 
                              result_stdout_parts[44], 
                              result_stdout_parts[46], 
                              result_stdout_parts[47], 
                              result_stdout_parts[48], 
                              result_stdout_parts[49],
                              
                              result_stdout_parts[50],                              
                              result_stdout_parts[51],
                              result_stdout_parts[52], 
                              result_stdout_parts[53], 
                              result_stdout_parts[54], 
                              result_stdout_parts[54], 
                              result_stdout_parts[56], 
                              result_stdout_parts[57], 
                              result_stdout_parts[58], 
                              result_stdout_parts[59],
                              
                              result_stdout_parts[60],                              
                              result_stdout_parts[61],
                              result_stdout_parts[62], 
                              result_stdout_parts[63], 
                              result_stdout_parts[64], 
                              result_stdout_parts[64], 
                              result_stdout_parts[66], 
                              result_stdout_parts[67], 
                              result_stdout_parts[68], 
                              result_stdout_parts[69],
                              
                              result_stdout_parts[70],                              
                              result_stdout_parts[71],
                              result_stdout_parts[72], 
                              result_stdout_parts[73], 
                              result_stdout_parts[74], 
                              result_stdout_parts[74], 
                              result_stdout_parts[76], 
                              result_stdout_parts[77], 
                              result_stdout_parts[78], 
                              result_stdout_parts[79],
                              
                              result_stdout_parts[80],                               
                              
                              ID)) 
               
            get_database_connection().commit()
            
            previous_recording_id = recording_id
            
        else:
            print(result.stderr)
           
def get_recording_array(recording_id):
    recordings_folder_with_path = base_folder + '/' + downloaded_recordings_folder
    filename = str(recording_id) + ".m4a"
    audio_in_path = recordings_folder_with_path + "/" + filename
    y, sr = librosa.load(audio_in_path)    
    return y, sr
    
    

def classify_onsets_using_weka_model_helper(onset, model_folder):     
    print('onset', onset)
    recording_id = onset[0]
    start_time_seconds = onset[1]
    duration_seconds = onset[2]
    actual_confirmed = onset[3]
    device_super_name = onset[4] 
    device_name = onset[5] 
    recordingDateTime = onset[6] 
    recordingDateTimeNZ = onset[7]
    
    # Skip if it already exists
    cur = get_database_connection().cursor()
    cur.execute("SELECT ID FROM model_run_result WHERE modelRunName = ? AND recording_id = ? AND startTime = ? AND duration = ?", (model_run_name, recording_id, start_time_seconds, duration_seconds)) 
    row = cur.fetchone()
    if row != None:
        print("Already done this one")
        return  
   
    create_single_focused_mel_spectrogram_for_model_input(recording_id, start_time_seconds, duration_seconds)
    
    # Create the input.arff file for this onset
    arff_filename_path = model_folder + '/' + weka_input_arff_filename  
    create_input_arff_file_for_single_onset_prediction(arff_filename_path, device_super_name)
    
    # Need to check arff file is there, otherwise run.jar will break later on
#     arff_filename_path = model_folder + '/' + weka_input_arff_filename        
    if not os.path.isfile(arff_filename_path):
        print(weka_input_arff_filename, " is missing") 
        return  
       
    result = run_model(model_folder)
    
    if result.returncode == 0:
        print(result.stdout)
        
        classNumber = (int)(result.stdout.split(",")[0])   
        
        predicted_class_name = parameters.class_names.split(",")[classNumber] 
        
        probability = result.stdout.split(",")[1]      
 
        print('It is predicted to be  ' , predicted_class_name, ' with probability of ',probability,  '\n')
        insert_model_run_result_into_database(parameters.model_run_name, recording_id, start_time_seconds, duration_seconds, None, predicted_class_name, probability, actual_confirmed, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ)
    
    else:
        print(result.stderr)
              

    
def insert_model_run_result_into_database(modelRunName, recording_id, startTime, duration, actual, predictedByModel, probability, actual_confirmed, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ):
       
    try:
        cur = get_database_connection().cursor()
        if actual_confirmed:
            sql = ''' INSERT INTO model_run_result(modelRunName, recording_id, startTime, duration, actual, predictedByModel, probability, actual_confirmed, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?,?) '''
            cur.execute(sql, (modelRunName, recording_id, startTime, duration, actual, predictedByModel, probability, actual_confirmed, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ))
        else:
            sql = ''' INSERT INTO model_run_result(modelRunName, recording_id, startTime, duration, actual, predictedByModel, probability, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?) '''
            cur.execute(sql, (modelRunName, recording_id, startTime, duration, actual, predictedByModel, probability, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ))
        
        get_database_connection().commit()
    except Exception as e:
        print(e, '\n')
        print('\t\tUnable to insert result' + str(recording_id) + ' ' + str(startTime), '\n')  
    
def play_clip(recording_id, start_time, duration, applyBandPassFilter):
    from pathlib import Path
    audio_in_path = getRecordingsFolder() + '/' + recording_id + '.m4a'
    print('audio_in_path ', audio_in_path)
    print('start_time ', start_time)
    print('duration ', duration)
    audio_out_folder = base_folder + '/' + temp_folder
    Path(audio_out_folder).mkdir(parents=True, exist_ok=True)
#     audio_out_path = base_folder + '/' + temp_folder + '/' + 'temp.wav'
    audio_out_path = audio_out_folder + '/' + 'temp.wav'
    
    print('audio_out_path ', audio_out_path)
    
    y, sr = librosa.load(audio_in_path, sr=None) 
    if applyBandPassFilter:
        y = apply_band_pass_filter(y, sr)
    y_amplified = np.int16(y/np.max(np.abs(y)) * 32767)
    y_amplified_start = sr * start_time
    y_amplified_end = (sr * start_time) + (sr * duration)
    y_amplified_to_play = y_amplified[int(y_amplified_start):int(y_amplified_end)]

    sf.write(audio_out_path, y_amplified_to_play, sr)

    os.system("aplay " + audio_out_path + " &")
    
def stop_clip():
#     https://www.reddit.com/r/learnpython/comments/9rxxj0/python_how_do_i_stop_a_audio_file_from_playing/
    os.system("killall aplay")
 
    
def create_arff_file_headder(output_folder, arff_filename, comments, relation, attribute_labels, attribute_features): 
         
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)  
        
    output_path_filename = output_folder + "/" + arff_filename
        
    f= open(output_path_filename,"w+")   
    f.write(comments)
    f.write("\n") 
    f.write(relation)
    f.write("\n") 
    f.write("\n") 
    for attribute_label in attribute_labels:
        f.write(attribute_label)
        f.write("\n")   
    for attribute_feature in attribute_features:
        f.write(attribute_feature)
        f.write("\n")   
        
    f.write("\n")    
    
    f.write("@data")  
    f.write("\n")  
    f.write("\n")  
        
    f.close()
  

        
def insert_onset_into_database(version, recording_id, start_time_seconds, duration_seconds):
    
    print('duration_seconds', duration_seconds)
    cur1 = get_database_connection().cursor()
    cur1.execute("SELECT device_super_name, device_name, recordingDateTime, recordingDateTimeNZ FROM recordings WHERE recording_id = ?", (recording_id,)) 
    rows = cur1.fetchall() 
    device_super_name = rows[0][0]  
    device_name = rows[0][1]
    recordingDateTime = rows[0][2]  
    recordingDateTimeNZ = rows[0][3] 
    
#     recordingDateTimeNZ = convert_time_zones(recordingDateTime)
    
    try:     
        sql = ''' INSERT INTO onsets(version, recording_id, start_time_seconds, duration_seconds, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ)
                  VALUES(?,?,?,?,?,?,?,?) '''
        cur2 = get_database_connection().cursor()
        cur2.execute(sql, (version, recording_id, start_time_seconds, duration_seconds, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ))
        get_database_connection().commit()
    except Exception as e:
        print(e, '\n')
        print('\t\tUnable to insert onest ' + str(recording_id), '\n')   
 
# https://stackoverflow.com/questions/25191620/creating-lowpass-filter-in-scipy-understanding-methods-and-units
def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y

def apply_lowpass_filter(y, sr):
    # Filter requirements.
    order = 6
       
#     cutoff = 1000  # desired cutoff frequency of the filter, Hz
    cutoff = 900  # desired cutoff frequency of the filter, Hz
    
    y = butter_lowpass_filter(y, cutoff, sr, order)
    
    return y
 

#https://dsp.stackexchange.com/questions/41184/high-pass-filter-in-python-scipy/41185#41185
def highpass_filter_with_parameters(y, sr, filter_stop_freq, filter_pass_freq ):
  
    filter_order = 1001
    
    # High-pass filter
    nyquist_rate = sr / 2.
    desired = (0, 0, 1, 1)
    bands = (0, filter_stop_freq, filter_pass_freq, nyquist_rate)
    filter_coefs = signal.firls(filter_order, bands, desired, nyq=nyquist_rate)
    
    # Apply high-pass filter
    filtered_audio = signal.filtfilt(filter_coefs, [1], y)
    return filtered_audio

    
def apply_band_pass_filter(y, sr):
    y = highpass_filter_with_parameters(y=y, sr=sr, filter_stop_freq=600, filter_pass_freq=650 )
    y = apply_lowpass_filter(y, sr)    
    return y
   
   
def create_onsets_in_local_db():
    
    cur = get_database_connection().cursor()  

    total_onset_pairs_including_more_than_40 = 0
    total_onset_pairs_including_not_including_more_40 = 0    
       
    # First need to find out what recordings have previously been used to create onsets - as we don't want to repeat
    cur.execute("SELECT recording_id, filename,  recordingDateTime FROM recordings WHERE processed_for_onsets IS NOT ? ORDER BY recording_id DESC", (onset_version,))
    recordings_with_no_onsets = cur.fetchall()
    print('There are ', len(recordings_with_no_onsets), ' recordings with no ', onset_version, ' onsets')     
    
    count = 0
    number_of_recordings_with_no_onsets = len(recordings_with_no_onsets)
    for recording_with_no_onsets in recordings_with_no_onsets: 
        try: 
            count += 1
            recording_id = recording_with_no_onsets[0]
            filename = recording_with_no_onsets[1]
           
            
            print('Processing ',count, ' of ', number_of_recordings_with_no_onsets)
            print('Recording id is ', recording_with_no_onsets) 
            count_of_onset_pairs_including_more_than_40, count_of_onset_pairs_including_not_including_more_40 = create_onsets_in_local_db_for_recording(filename)
            
            # Update recordings table to show that this recording has been processed for onsets
            cur.execute("UPDATE recordings SET processed_for_onsets = ? WHERE recording_id = ?", (onset_version, recording_id,))  
            get_database_connection().commit()
            
            total_onset_pairs_including_more_than_40 += count_of_onset_pairs_including_more_than_40
            total_onset_pairs_including_not_including_more_40 += count_of_onset_pairs_including_not_including_more_40
            print('total_onset_pairs_including_more_than_40:', total_onset_pairs_including_more_than_40)
            print('total_onset_pairs_including_not_including_more_40:', total_onset_pairs_including_not_including_more_40, '\n')
        except Exception as e:
#             print(e, '\n')
            print('Error processing file ', recording_id, '\n')
            cur.execute("UPDATE recordings SET processed_for_onsets = -1 WHERE recording_id = ?", (recording_id,))  
            get_database_connection().commit()    

     
def create_onsets_in_local_db_for_recording(filename): 
    try:

        recordings_folder_with_path = base_folder + '/' + downloaded_recordings_folder
        
        count_of_onset_pairs_including_more_than_40 = 0
        count_of_onset_pairs_including_not_including_more_40 = 0
        
        audio_in_path = recordings_folder_with_path + "/" + filename
        
        # Some recordings are not available
        if not os.path.isfile(audio_in_path):
            print("This recording is not available ", filename)
            # Update the db to say that it has been processed
   
        y, sr = librosa.load(audio_in_path)
        y_filtered = butter_bandpass_filter(y, 600, 1200, sr, order=6)    
        y_filtered_and_noise_reduced = noise_reduce(y_filtered, sr)
    
        onsets = find_squawk_location_secs_in_single_recording(y_filtered_and_noise_reduced,sr)          
    
        number_of_onsets = len(onsets)
        if not number_of_onsets == 0:
            if number_of_onsets > 40:
                count_of_onset_pairs_including_more_than_40 += number_of_onsets
            else:                
                
                count_of_onset_pairs_including_more_than_40 += number_of_onsets
                count_of_onset_pairs_including_not_including_more_40 += number_of_onsets                        
           
                recording_id = filename.split('.')[0]  
                insert_onset_list_into_db(recording_id, onsets)
                
        return count_of_onset_pairs_including_more_than_40, count_of_onset_pairs_including_not_including_more_40 

    except Exception:
        pass
                    
def insert_onset_list_into_db(recording_id, onsets):
    global squawk_duration_seconds
    prev_onset = -1
    for onset in onsets:
        if prev_onset == -1:
            print("onset " , onset)    
            insert_onset_into_database(onset_version, recording_id, onset, squawk_duration_seconds)
            prev_onset =  onset
        else:
            if (onset - prev_onset) < (squawk_duration_seconds + 0.1):
                print("Onset too close to previous, not inserting into database " , onset) 
            else:
                prev_onset = onset 
                insert_onset_into_database(onset_version, recording_id, onset, squawk_duration_seconds)
                print("Inserting onset into database " , onset)

def find_squawk_location_secs_in_single_recording(y, sr):

    squawks = FindSquawks(y, sr)
    squawks_secs = []

    for squawk in squawks:
        squawk_start = squawk['start']
        squawk_start_sec = squawk_start / sr
        squawks_secs.append(round(squawk_start_sec, 1))
        
    return squawks_secs



def FindSquawks(source, sampleRate):
    result = []
    source = source / max(source)
    startIndex = None
    stopIndex = None
    smallTime = int(sampleRate*0.1)
    tolerance = 0.2
    
    for index in range(source.shape[0]):
        if not startIndex:
            if abs(source[index]) > tolerance:
                startIndex = index
                stopIndex = index
            continue
        if abs(source[index]) > tolerance:
            stopIndex = index
        elif index > stopIndex+smallTime:
            duration = (stopIndex-startIndex)/sampleRate
            if duration > 0.05:
                squawk = {'start': startIndex,
                          'stop': stopIndex, 'duration': duration}
                squawk['rms'] = rms(source[startIndex:stopIndex])
                result.append(squawk)
            startIndex = None
    return result


def rms(x):
    """Root-Mean-Square."""
    return np.sqrt(x.dot(x) / x.size)

def create_focused_mel_spectrogram_jps_using_onset_pairs():
    mel_spectrograms_out_folder_path = base_folder + '/' + run_folder + '/' + spectrograms_for_model_creation_folder 
    if not os.path.exists(mel_spectrograms_out_folder_path):
        os.makedirs(mel_spectrograms_out_folder_path)
       
    count = 0
    onsets = get_onsets_stored_locally('')   
      
#     for entry in os.scandir(onset_pairs_folder_path): 
    for onset in onsets:
        try:
            print('Processing onset ', count, ' of ', len(onsets), ' onsets.')
            count+=1    

            version_from_onset = onset[0] 
            recording_id = onset[1] 
            start_time_seconds = onset[2]
            duration_seconds = onset[3]
            
            audio_filename = str(recording_id) + '.m4a'
            audio_in_path = base_folder + '/' + downloaded_recordings_folder + '/' +  audio_filename 
            image_out_name = version_from_onset + '_' + str(recording_id) + '_' + str(start_time_seconds) + '_' + str(duration_seconds) + '.jpg'
            print('image_out_name', image_out_name)           
           
            image_out_path = mel_spectrograms_out_folder_path + '/' + image_out_name
            
            y, sr = librosa.load(audio_in_path, sr=None) 
            
            start_time_seconds_float = float(start_time_seconds)            
            
            start_position_array = int(sr * start_time_seconds_float)              
                       
            end_position_array = start_position_array + int((sr * duration_seconds))
                       
            if end_position_array > y.shape[0]:
                print('Clip would end after end of recording')
                continue
                
            y_part = y[start_position_array:end_position_array]  
            mel_spectrogram = librosa.feature.melspectrogram(y=y_part, sr=sr, n_mels=32, fmin=700,fmax=1000)
            
#             pylab.axis('off') # no axis
            plt.axis('off') # no axis
            plt.axes([0., 0., 1., 1.], frameon=False, xticks=[], yticks=[]) # Remove the white edge
            librosa.display.specshow(mel_spectrogram, cmap='binary') #https://matplotlib.org/examples/color/colormaps_reference.html
            plt.savefig(image_out_path, bbox_inches=None, pad_inches=0)
            plt.close()
            
        except Exception as e:
            print(e, '\n')
            print('Error processing onset ', onset)

def create_spectrogram_jpg_files_for_next_model_run_or_model_test(testing):
    
    cur = get_database_connection().cursor()
    
    if testing:
        mel_spectrograms_out_folder_path = base_folder + '/' + run_folder + '/' + spectrograms_for_model_testing_folder 
        cur.execute("SELECT ID, recording_id, startTime, actual_confirmed FROM model_run_result WHERE modelRunName = ? AND actual_confirmed IS NOT NULL AND used_to_create_model IS NULL", (model_run_name, )) 
    else:        
        mel_spectrograms_out_folder_path = base_folder + '/' + run_folder + '/' + spectrograms_for_model_creation_folder 
        cur.execute("SELECT ID, recording_id, startTime, actual_confirmed FROM model_run_result WHERE modelRunName = ? AND actual_confirmed IS NOT NULL", (model_run_name, ))
        
        # Also going to take this opportunity to create the model_run directory so it is available later in Weka for saving the model
        weka_model_folder_path = base_folder + '/' + run_folder + '/' + weka_model_folder 
        if not os.path.exists(weka_model_folder_path):
            os.makedirs(weka_model_folder_path)
        
    if not os.path.exists(mel_spectrograms_out_folder_path):
        os.makedirs(mel_spectrograms_out_folder_path)
        
        
  

    count = 0
    

    rows = cur.fetchall()  
    
    for row in rows:
        try:
            print('Processing row ', count, ' of ', len(rows), ' rows.')
            count+=1
            print('row ', row)
            recording_id = row[1] 
            start_time_seconds = row[2]
            actual_confirmed = row[3]  
            
            if not actual_confirmed:
                # actual_confirmed will be null for testing
                actual_confirmed = "unknown"
#             
            audio_filename = str(recording_id) + '.m4a'
            audio_in_path = base_folder  + '/' + downloaded_recordings_folder + '/' +  audio_filename 
            
            # Also need the device super name in the filename so that it can be used by the model
            cur1 = get_database_connection().cursor()    
            cur1.execute("select distinct device_super_name from recordings where recording_id = ?", (recording_id,))      
            device_super_name = cur1.fetchall()
            print('device_super_name', device_super_name[0][0])
                
#             print('recording_id ', recording_id)
            
#             image_out_name = actual_confirmed + '$' + str(recording_id) + '$' + str(start_time_seconds) + '.jpg'
            image_out_name = device_super_name[0][0] + '$' + actual_confirmed + '$' + str(recording_id) + '$' + str(start_time_seconds) + '.jpg'
            print('image_out_name', image_out_name)           
            
            image_out_path = mel_spectrograms_out_folder_path + '/' + image_out_name
             
            y, sr = librosa.load(audio_in_path, sr=None) 
             
            start_time_seconds_float = float(start_time_seconds)            
             
            start_position_array = int(sr * start_time_seconds_float)              
                        
            end_position_array = start_position_array + int((sr * morepork_more_pork_call_duration))
#                        
            if end_position_array > y.shape[0]:
                print('Clip would end after end of recording')
                continue
                 
            y_part = y[start_position_array:end_position_array]  
          
            mel_spectrogram = librosa.feature.melspectrogram(y=y_part, sr=sr, n_mels=32, fmin=700,fmax=1000)
             
            plt.axis('off') # no axis
            plt.axes([0., 0., 1., 1.], frameon=False, xticks=[], yticks=[]) # Remove the white edge
            librosa.display.specshow(mel_spectrogram, cmap='binary') #https://matplotlib.org/examples/color/colormaps_reference.html
            plt.savefig(image_out_path, bbox_inches=None, pad_inches=0)
            plt.close()
             
        except Exception as e:
            print(e, '\n')
           
            
            
def get_single_create_focused_mel_spectrogram(recording_id, start_time_seconds, duration_seconds):

    temp_display_images_folder_path = base_folder + '/' + run_folder + '/' + temp_display_images_folder 
    if not os.path.exists(temp_display_images_folder_path):
        os.makedirs(temp_display_images_folder_path)         

    try:
        
        audio_filename = str(recording_id) + '.m4a'
        audio_in_path = base_folder + '/' + downloaded_recordings_folder + '/' +  audio_filename 
        image_out_name = 'temp_spectrogram.jpg'
        print('image_out_name', image_out_name)           
       
        image_out_path = temp_display_images_folder_path + '/' + image_out_name
        
        y, sr = librosa.load(audio_in_path, sr=None)      
               
        start_time_seconds_float = float(start_time_seconds)            
        
        start_position_array = int(sr * start_time_seconds_float)              
                   
        end_position_array = start_position_array + int((sr * duration_seconds))                  
                    
        y_part = y[start_position_array:end_position_array]  
        mel_spectrogram = librosa.feature.melspectrogram(y=y_part, sr=sr, n_mels=32, fmin=700,fmax=1000)
        
        plt.axis('off') # no axis
        plt.axes([0., 0., 1., 1.], frameon=False, xticks=[], yticks=[]) # Remove the white edge
        librosa.display.specshow(mel_spectrogram, cmap='binary') #https://matplotlib.org/examples/color/colormaps_reference.html
        plt.savefig(image_out_path, bbox_inches=None, pad_inches=0)
        plt.close()
        
        return get_image(image_out_path)
        
    except Exception as e:
        print(e, '\n')
        print('Error processing onset ', onset)
        

def get_single_create_focused_mel_spectrogram_for_creating_test_data(recording_id, min_freq, max_freq):
    
    print("min_freq ", min_freq)
    print("max_freq ", max_freq)

    temp_display_images_folder_path = base_folder + '/' + run_folder + '/' + temp_display_images_folder 
    if not os.path.exists(temp_display_images_folder_path):
        os.makedirs(temp_display_images_folder_path)         

    try:
        
        audio_filename = str(recording_id) + '.m4a'
        audio_in_path = base_folder + '/' + downloaded_recordings_folder + '/' +  audio_filename 
        image_out_name = 'temp_spectrogram.jpg'
        print('image_out_name', image_out_name)           
       
        image_out_path = temp_display_images_folder_path + '/' + image_out_name
        
        y, sr = librosa.load(audio_in_path, sr=None) 

        mel_spectrogram = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=32, fmin=min_freq,fmax=max_freq)
         
        plt.axis('off') # no axis
        plt.axes([0., 0., 1., 1.], frameon=False, xticks=[], yticks=[]) # Remove the white edge
        librosa.display.specshow(mel_spectrogram, cmap='binary') #https://matplotlib.org/examples/color/colormaps_reference.html
        plt.savefig(image_out_path, bbox_inches=None, pad_inches=0)
        plt.close()
        
        return get_image_for_for_creating_test_data(image_out_path)
        
    except Exception as e:
        print(e, '\n')
        print('Error processing onset ', onset)
        
def create_single_focused_mel_spectrogram_for_model_input(recording_id, start_time_seconds, duration_seconds, y, sr):

    mel_spectrograms_out_folder_path = base_folder + '/' + run_folder + '/' + weka_model_folder + '/' + single_spectrogram_for_classification_folder 
    if not os.path.exists(mel_spectrograms_out_folder_path):
        os.makedirs(mel_spectrograms_out_folder_path)  
 
    try:        

        image_out_name = 'input_image.jpg'
         
       
        image_out_path = mel_spectrograms_out_folder_path + '/' + image_out_name
        
#         y, sr = librosa.load(audio_in_path, sr=None)      
               
        start_time_seconds_float = float(start_time_seconds)            
        
        start_position_array = int(sr * start_time_seconds_float)              
                   
        end_position_array = start_position_array + int((sr * duration_seconds))                  
                    
        y_part = y[start_position_array:end_position_array]  
        mel_spectrogram = librosa.feature.melspectrogram(y=y_part, sr=sr, n_mels=32, fmin=700,fmax=1000)
        
        plt.axis('off') # no axis
        plt.axes([0., 0., 1., 1.], frameon=False, xticks=[], yticks=[]) # Remove the white edge
        librosa.display.specshow(mel_spectrogram, cmap='binary') #https://matplotlib.org/examples/color/colormaps_reference.html
        plt.savefig(image_out_path, bbox_inches=None, pad_inches=0)
        plt.close()       

        
    except Exception as e:
        print(e, '\n')
        print('Error processing onset ', onset)
        

           
def get_single_waveform_image(recording_id, start_time_seconds, duration_seconds):

    temp_display_images_folder_path = base_folder + '/' + run_folder + '/' + temp_display_images_folder 
    if not os.path.exists(temp_display_images_folder_path):
        os.makedirs(temp_display_images_folder_path)         

    try:
        
        audio_filename = str(recording_id) + '.m4a'
        audio_in_path = base_folder + '/' + downloaded_recordings_folder + '/' +  audio_filename 
        image_out_name = 'temp_waveform.jpg'
        print('image_out_name', image_out_name)           
       
        image_out_path = temp_display_images_folder_path + '/' + image_out_name
        
        y, sr = librosa.load(audio_in_path, sr=None) 
        
        start_time_seconds_float = float(start_time_seconds)            
        
        start_position_array = int(sr * start_time_seconds_float)              
                   
        end_position_array = start_position_array + int((sr * duration_seconds))                  
                    
        y_part = y[start_position_array:end_position_array]  
    
        plt.axis('off') # no axis
        plt.axes([0., 0., 1., 1.], frameon=False, xticks=[], yticks=[]) # Remove the white edge
        librosa.display.waveplot(y=y_part, sr=sr)
        plt.savefig(image_out_path, bbox_inches=None, pad_inches=0)
        plt.close()
        
        return get_image(image_out_path)
        
    except Exception as e:
        print(e, '\n')
        print('Error processing onset ', onset)
               
def get_image(image_name_path): 
        
    image = Image.open(image_name_path)
    [imageSizeWidth, imageSizeHeight] = image.size
    image = image.resize((int(imageSizeWidth/2),int(imageSizeHeight/2)), Image.ANTIALIAS)
    spectrogram_image = ImageTk.PhotoImage(image)
    return spectrogram_image

def get_image_for_for_creating_test_data(image_name_path): 
        
    image = Image.open(image_name_path)
    print("Image size is ", image.size)
    [imageSizeWidth, imageSizeHeight] = image.size
#     image = image.resize((int(imageSizeWidth*4),int(imageSizeHeight*2)), Image.ANTIALIAS)
#     image = image.resize((int(imageSizeWidth*4),int(imageSizeHeight*4)), Image.ANTIALIAS)
#     image = image.resize((int(imageSizeWidth*4),int(imageSizeHeight)), Image.ANTIALIAS)
#     image = image.resize((int(imageSizeWidth*3.9),int(imageSizeHeight)), Image.ANTIALIAS)
#     image = image.resize((int(imageSizeWidth*3.85),int(imageSizeHeight)), Image.ANTIALIAS)
    image = image.resize((int(imageSizeWidth*3.84),int(imageSizeHeight)), Image.ANTIALIAS)

    print("Image size is ", image.size)
    spectrogram_image = ImageTk.PhotoImage(image)
    return spectrogram_image

def get_unique_model_run_names():   
    cur = get_database_connection().cursor()
    cur.execute("SELECT DISTINCT modelRunName FROM model_run_result") 
    rows = cur.fetchall()  
    
    unique_model_run_names = []
    for row in rows:
        unique_model_run_names.append(row[0])
        
    return unique_model_run_names  

def get_unique_locations(table_name):   
    cur = get_database_connection().cursor()
    if table_name == 'recordings':
        cur.execute("SELECT DISTINCT device_super_name FROM recordings") 
    else:
        cur.execute("SELECT DISTINCT device_super_name FROM tags") 
    rows = cur.fetchall()  
    
    unique_locations = []
    unique_locations.append('Not Used')
    for row in rows:
        unique_locations.append(row[0])        
        
    return unique_locations  

    
def create_arff_file_for_weka_image_filter_input(test_arff):
    
    run_folder_path = base_folder + '/' + run_folder
    
    if test_arff:
        spectrograms_folder_path = run_folder_path + '/' + spectrograms_for_model_testing_folder
        f= open(run_folder_path + '/' + arff_file_for_weka_model_testing,"w+")
    else:        
        spectrograms_folder_path = run_folder_path + '/' + spectrograms_for_model_creation_folder 
        f= open(run_folder_path + '/' + arff_file_for_weka_model_creation,"w+")     
   
    f.write('@relation ' + relation_name + '\r\n')
    f.write('@attribute filename string' + '\r\n')
    # Add in the device super names attribute
    # Get list of unique 
    cur = get_database_connection().cursor()    
    cur.execute("select distinct device_super_name from recordings") # This means that any device has had recordings downloaded will be included in arff file header. Previously I was using model_run_result, which wouldn't have new names.   
    device_super_names = cur.fetchall()
    numberOfSuperNames = len(device_super_names)
    print('numberOfSuperNames ', numberOfSuperNames)
    
    device_super_names_str = ''
    print(device_super_names_str)
    
    count = 0
    for device_super_name in device_super_names:  
        count+=1    
        print(device_super_name[0])  
        device_super_names_str+= device_super_name[0]
        if count < numberOfSuperNames: # Do not want a comma at the end of the string for arff format
            device_super_names_str+= ', '
   
    print(device_super_names_str)
    f.write('@attribute deviceSuperName {' + device_super_names_str +'}' + '\r\n')
    
    f.write('@attribute class {' + class_names +'}' + '\r\n')
    f.write('@data' + '\r\n')    
     
   
    for filename in os.listdir(spectrograms_folder_path):
        filename_parts = filename.split('$')
        deviceSuperName = filename_parts[0]
        class_type = filename_parts[1]
        print('image', filename)
        print('class_type', class_type)
#         f.write(filename +',' + class_type + '\r\n')deviceSuperName
        f.write(filename +',' + deviceSuperName +',' + class_type + '\r\n')
        
    f.close()
    
   
    
def create_arff_file_for_weka(test_arff, firstDate, lastDate):
#  IF test_arff IS true, then just create an arff file for a single onset - to be used to give to the model for a class prediction

    # https://stackoverflow.com/questions/8187288/sql-select-between-dates
    firstDateStr = firstDate.strftime("%Y-%m-%d") + ':00:00:00'
    lastDateStr = lastDate.strftime("%Y-%m-%d") + ':23:59:59'
    
    run_folder_path = base_folder + '/' + run_folder
    
    if test_arff:       
        f= open(run_folder_path + '/' + arff_file_for_weka_model_testing,"w+")
    else:
        f= open(run_folder_path + '/' + arff_file_for_weka_model_creation,"w+") 
        f_csv_file_for_keeping_track_of_onsets_used_to_create_model = open(run_folder_path + '/' + csv_file_for_keeping_track_of_onsets_used_to_create_model,"w+") 
       
#     f= open(run_folder_path + '/' + arff_file_for_weka_model_creation,"w+")
    f.write('@relation ' + relation_name + '\r\n')
#     f.write('@attribute filename string' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram0\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram1\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram2\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram3\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram4\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram5\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram6\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram7\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram8\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram9\' numeric' + '\r\n')
    
    f.write('@attribute \'MPEG-7 Edge Histogram10\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram11\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram12\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram13\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram14\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram15\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram16\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram17\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram18\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram19\' numeric' + '\r\n')
    
    f.write('@attribute \'MPEG-7 Edge Histogram20\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram21\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram22\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram23\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram24\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram25\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram26\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram27\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram28\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram29\' numeric' + '\r\n')
    
    f.write('@attribute \'MPEG-7 Edge Histogram30\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram31\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram32\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram33\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram34\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram35\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram36\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram37\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram38\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram39\' numeric' + '\r\n')
    
    f.write('@attribute \'MPEG-7 Edge Histogram40\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram41\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram42\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram43\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram44\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram45\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram46\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram47\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram48\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram49\' numeric' + '\r\n')
    
    f.write('@attribute \'MPEG-7 Edge Histogram50\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram51\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram52\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram53\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram54\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram55\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram56\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram57\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram58\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram59\' numeric' + '\r\n')
    
    f.write('@attribute \'MPEG-7 Edge Histogram60\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram61\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram62\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram63\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram64\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram65\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram66\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram67\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram68\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram69\' numeric' + '\r\n')
    
    f.write('@attribute \'MPEG-7 Edge Histogram70\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram71\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram72\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram73\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram74\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram75\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram76\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram77\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram78\' numeric' + '\r\n')
    f.write('@attribute \'MPEG-7 Edge Histogram79\' numeric' + '\r\n')
    


    # Add in the device super names attribute
    # Get list of unique 
    cur = get_database_connection().cursor()    
#     cur.execute("select distinct device_super_name from model_run_result where modelRunName = ?", (model_run_name,))    
    cur.execute("select distinct device_super_name from recordings") # This means that any device has had recordings downloaded will be included in arff file header. Previously I was using model_run_result, which wouldn't have new names.   
    device_super_names = cur.fetchall()
    numberOfSuperNames = len(device_super_names)
    print('numberOfSuperNames ', numberOfSuperNames)
    
    device_super_names_str = ''
    print(device_super_names_str)
    
    count = 0
    for device_super_name in device_super_names:  
        count+=1    
        print(device_super_name[0])  
        device_super_names_str+= device_super_name[0]
        if count < numberOfSuperNames: # Do not want a comma at the end of the string for arff format
            device_super_names_str+= ', '
   
    print(device_super_names_str)
    f.write('@attribute deviceSuperName {' + device_super_names_str +'}' + '\r\n')
    
    f.write('@attribute class {' + class_names +'}' + '\r\n')
    f.write('@data' + '\r\n')    
    
    sql = '''SELECT
        MPEG7_Edge_Histogram0,
        MPEG7_Edge_Histogram1,
        MPEG7_Edge_Histogram2,
        MPEG7_Edge_Histogram3,
        MPEG7_Edge_Histogram4,
        MPEG7_Edge_Histogram5,
        MPEG7_Edge_Histogram6,
        MPEG7_Edge_Histogram7,
        MPEG7_Edge_Histogram8,
        MPEG7_Edge_Histogram9,
        
        MPEG7_Edge_Histogram10, 
        MPEG7_Edge_Histogram11,
        MPEG7_Edge_Histogram12,
        MPEG7_Edge_Histogram13,
        MPEG7_Edge_Histogram14,
        MPEG7_Edge_Histogram15,
        MPEG7_Edge_Histogram16,
        MPEG7_Edge_Histogram17,
        MPEG7_Edge_Histogram18,
        MPEG7_Edge_Histogram19,
        
        MPEG7_Edge_Histogram20,
        MPEG7_Edge_Histogram21,
        MPEG7_Edge_Histogram22,
        MPEG7_Edge_Histogram23,
        MPEG7_Edge_Histogram24,
        MPEG7_Edge_Histogram25,
        MPEG7_Edge_Histogram26,
        MPEG7_Edge_Histogram27,
        MPEG7_Edge_Histogram28,
        MPEG7_Edge_Histogram29,
        
        MPEG7_Edge_Histogram30,
        MPEG7_Edge_Histogram31,
        MPEG7_Edge_Histogram32,
        MPEG7_Edge_Histogram33,
        MPEG7_Edge_Histogram34,
        MPEG7_Edge_Histogram35,
        MPEG7_Edge_Histogram36,
        MPEG7_Edge_Histogram37,
        MPEG7_Edge_Histogram38,
        MPEG7_Edge_Histogram39,
        
        MPEG7_Edge_Histogram40, 
        MPEG7_Edge_Histogram41,
        MPEG7_Edge_Histogram42,
        MPEG7_Edge_Histogram43,
        MPEG7_Edge_Histogram44,
        MPEG7_Edge_Histogram45,
        MPEG7_Edge_Histogram46,
        MPEG7_Edge_Histogram47,
        MPEG7_Edge_Histogram48,
        MPEG7_Edge_Histogram49,
        
        MPEG7_Edge_Histogram50, 
        MPEG7_Edge_Histogram51,
        MPEG7_Edge_Histogram52,
        MPEG7_Edge_Histogram53,
        MPEG7_Edge_Histogram54,
        MPEG7_Edge_Histogram55,
        MPEG7_Edge_Histogram56,
        MPEG7_Edge_Histogram57,
        MPEG7_Edge_Histogram58,
        MPEG7_Edge_Histogram59,
        
        MPEG7_Edge_Histogram60,
        MPEG7_Edge_Histogram61,
        MPEG7_Edge_Histogram62,
        MPEG7_Edge_Histogram63,
        MPEG7_Edge_Histogram64,
        MPEG7_Edge_Histogram65,
        MPEG7_Edge_Histogram66,
        MPEG7_Edge_Histogram67,
        MPEG7_Edge_Histogram68,
        MPEG7_Edge_Histogram69,
        
        MPEG7_Edge_Histogram70,
        MPEG7_Edge_Histogram71,
        MPEG7_Edge_Histogram72,
        MPEG7_Edge_Histogram73,
        MPEG7_Edge_Histogram74,
        MPEG7_Edge_Histogram75,
        MPEG7_Edge_Histogram76,
        MPEG7_Edge_Histogram77,
        MPEG7_Edge_Histogram78,
        MPEG7_Edge_Histogram79,        
                
        device_super_name, 
        actual_confirmed,
        recording_id,
        start_time_seconds,
        recordingDateTimeNZ
            
    
        FROM onsets        

        WHERE actual_confirmed IS NOT NULL AND MPEG7_Edge_Histogram0 IS NOT NULL AND strftime('%Y-%m-%d:%H-%M-%S', recordingDateTimeNZ) NOT BETWEEN ? AND ?
        '''
    cur.execute(sql,(firstDateStr, lastDateStr))      
    confirmedOnsets = cur.fetchall()
    
    for confirmedOnset in confirmedOnsets:
        print(confirmedOnset[84])
    
    for confirmedOnset in confirmedOnsets:
        f.write(str(confirmedOnset[0]) +',' + 
                str(confirmedOnset[1]) +',' + 
                str(confirmedOnset[2]) +',' +
                str(confirmedOnset[3]) +',' +
                str(confirmedOnset[4]) +',' +
                str(confirmedOnset[5]) +',' +
                str(confirmedOnset[6]) +',' +
                str(confirmedOnset[7]) +',' +
                str(confirmedOnset[8]) +',' +
                str(confirmedOnset[9]) +',' +
                
                str(confirmedOnset[10]) +',' + 
                str(confirmedOnset[11]) +',' + 
                str(confirmedOnset[12]) +',' +
                str(confirmedOnset[13]) +',' +
                str(confirmedOnset[14]) +',' +
                str(confirmedOnset[15]) +',' +
                str(confirmedOnset[16]) +',' +
                str(confirmedOnset[17]) +',' +
                str(confirmedOnset[18]) +',' +
                str(confirmedOnset[19]) +',' +
                
                str(confirmedOnset[20]) +',' + 
                str(confirmedOnset[21]) +',' + 
                str(confirmedOnset[22]) +',' +
                str(confirmedOnset[23]) +',' +
                str(confirmedOnset[24]) +',' +
                str(confirmedOnset[25]) +',' +
                str(confirmedOnset[26]) +',' +
                str(confirmedOnset[27]) +',' +
                str(confirmedOnset[28]) +',' +
                str(confirmedOnset[29]) +',' +
                
                str(confirmedOnset[30]) +',' + 
                str(confirmedOnset[31]) +',' + 
                str(confirmedOnset[32]) +',' +
                str(confirmedOnset[33]) +',' +
                str(confirmedOnset[34]) +',' +
                str(confirmedOnset[35]) +',' +
                str(confirmedOnset[36]) +',' +
                str(confirmedOnset[37]) +',' +
                str(confirmedOnset[38]) +',' +
                str(confirmedOnset[39]) +',' +
                
                str(confirmedOnset[40]) +',' + 
                str(confirmedOnset[41]) +',' + 
                str(confirmedOnset[42]) +',' +
                str(confirmedOnset[43]) +',' +
                str(confirmedOnset[44]) +',' +
                str(confirmedOnset[45]) +',' +
                str(confirmedOnset[46]) +',' +
                str(confirmedOnset[47]) +',' +
                str(confirmedOnset[48]) +',' +
                str(confirmedOnset[49]) +',' +
                
                str(confirmedOnset[50]) +',' + 
                str(confirmedOnset[51]) +',' + 
                str(confirmedOnset[52]) +',' +
                str(confirmedOnset[53]) +',' +
                str(confirmedOnset[54]) +',' +
                str(confirmedOnset[55]) +',' +
                str(confirmedOnset[56]) +',' +
                str(confirmedOnset[57]) +',' +
                str(confirmedOnset[58]) +',' +
                str(confirmedOnset[59]) +',' +
                
                str(confirmedOnset[60]) +',' + 
                str(confirmedOnset[61]) +',' + 
                str(confirmedOnset[62]) +',' +
                str(confirmedOnset[63]) +',' +
                str(confirmedOnset[64]) +',' +
                str(confirmedOnset[65]) +',' +
                str(confirmedOnset[66]) +',' +
                str(confirmedOnset[67]) +',' +
                str(confirmedOnset[68]) +',' +
                str(confirmedOnset[69]) +',' +
                
                str(confirmedOnset[70]) +',' + 
                str(confirmedOnset[71]) +',' + 
                str(confirmedOnset[72]) +',' +
                str(confirmedOnset[73]) +',' +
                str(confirmedOnset[74]) +',' +
                str(confirmedOnset[75]) +',' +
                str(confirmedOnset[76]) +',' +
                str(confirmedOnset[77]) +',' +
                str(confirmedOnset[78]) +',' +
                str(confirmedOnset[79]) +',' +
              
                confirmedOnset[80] +',' +           # This is deviceSuperName
                confirmedOnset[81] + '\r\n')        # This is confirmed sound/class type   
        f_csv_file_for_keeping_track_of_onsets_used_to_create_model.write(parameters.model_run_name + "," + str(confirmedOnset[82]) + "," + str(confirmedOnset[83]) + '\r\n') 
     
           
    f.close()
    f_csv_file_for_keeping_track_of_onsets_used_to_create_model.close();
          
            
def create_folders_for_next_run():
    next_run_folder = parameters.base_folder + '/' + run_folder
    if not os.path.exists(next_run_folder):
        os.makedirs(next_run_folder) 
        
        
    weka_model_folder_path = parameters.base_folder + '/' + run_folder + '/' + weka_model_folder  
    if not os.path.exists(weka_model_folder_path):
        os.makedirs(weka_model_folder_path) 
        
    spectrograms_for_model_creation_folder_path = parameters.base_folder + '/' + run_folder + '/' + spectrograms_for_model_creation_folder  
    if not os.path.exists(spectrograms_for_model_creation_folder_path):
        os.makedirs(spectrograms_for_model_creation_folder_path) 
        
    single_spectrogram_for_classification_folder_path = parameters.base_folder + '/' + run_folder + '/' + weka_model_folder + '/' + single_spectrogram_for_classification_folder  
    if not os.path.exists(single_spectrogram_for_classification_folder_path):
        os.makedirs(single_spectrogram_for_classification_folder_path) 
        
def get_single_recording_info_from_local_db(recording_id):

    cur = get_database_connection().cursor()
    cur.execute("SELECT device_super_name, recordingDateTime FROM recordings WHERE recording_id = ?", (recording_id,))  
  
    recordings = cur.fetchall()
     
    single_recording =  recordings[0]   
    device_super_name = single_recording[0]
    recordingDateTime = single_recording[1]
    
    date_time_obj = datetime.strptime(recordingDateTime, "%Y-%m-%dT%H:%M:%S.000Z")    
    date_time_obj_Zulu = timezone('Zulu').localize(date_time_obj)

    fmt = "%Y-%m-%d %H:%M"
    
    date_time_obj_NZ = date_time_obj_Zulu.astimezone(timezone('Pacific/Auckland'))

    return device_super_name, date_time_obj_NZ.strftime(fmt)

def update_onsets_with_latest_model_run_actual_confirmed():
    cur = get_database_connection().cursor()
    previous_model_run = "2019_12_05_1"
    
    cur.execute("SELECT recording_id, startTime, actual_confirmed FROM model_run_result WHERE actual_confirmed IS NOT NULL AND modelRunName = ?", (previous_model_run,)) 
    
    confirmed_rows = cur.fetchall()
    
    for confirmed_row in confirmed_rows:
       
        recording_id = confirmed_row[0]
        startTime = confirmed_row[1]
        actual_confirmed = confirmed_row[2]
        
        print(recording_id, ' ', startTime, ' ', actual_confirmed)
        
        cur2 = get_database_connection().cursor()                
        cur2.execute("UPDATE onsets SET actual_confirmed = ? WHERE recording_id = ? AND start_time_seconds = ?", (actual_confirmed, recording_id, startTime))  
                
        get_database_connection().commit()
    

def update_onsets_device_super_name():
    # Used to back fill recording_id into onsets table
    cur = get_database_connection().cursor()
    cur.execute("SELECT ID, recording_id FROM onsets ") 
    onsets = cur.fetchall()
    count = 0
    total = len(onsets)
    for onset in onsets:
        count+=1
        print('Updating ', count, ' of ', total)
        ID = onset[0]
        recording_id = onset[1]
        
        cur1 = get_database_connection().cursor()
        cur1.execute("SELECT device_super_name FROM recordings WHERE recording_id = ?", (recording_id,)) 
        rows = cur1.fetchall() 
        device_super_name = rows[0][0]
        
        cur2 = get_database_connection().cursor()                
        cur2.execute("UPDATE onsets SET device_super_name = ? WHERE ID = ?", (device_super_name, ID))  
                
        get_database_connection().commit()
        
def update_model_run_result_device_super_name():
    # Used to back fill recording_id into onsets table
    cur = get_database_connection().cursor()
    cur.execute("SELECT ID, recording_id FROM model_run_result ") 
    model_run_results = cur.fetchall()
    count = 0
    total = len(model_run_results)
    for model_run_result in model_run_results:
        count+=1
        print('Updating ', count, ' of ', total)
        ID = model_run_result[0]
        recording_id = model_run_result[1]
        
        cur1 = get_database_connection().cursor()
        cur1.execute("SELECT device_super_name FROM recordings WHERE recording_id = ?", (recording_id,)) 
        rows = cur1.fetchall() 
        device_super_name = rows[0][0]
        
        cur2 = get_database_connection().cursor()                
        cur2.execute("UPDATE model_run_result SET device_super_name = ? WHERE ID = ?", (device_super_name, ID))  
                
        get_database_connection().commit()
        
        
def test_query():        
    cur = get_database_connection().cursor()
#     cur.execute("SELECT ID, device_super_name FROM model_run_result WHERE modelRunName = '2019_12_11_1' AND device_super_name = 'Hammond Park' ORDER BY recording_id DESC, startTime ASC")
    cur.execute("SELECT ID, device_super_name FROM model_run_result WHERE modelRunName = '2019_12_11_1' ORDER BY recording_id DESC, startTime ASC")  
    model_run_results = cur.fetchall() 
    count = 0
    total = len(model_run_results)
    for model_run_result in model_run_results:
        count+=1
        print('Processing ', count, ' of ', total)
        ID = model_run_result[0]
        device_super_name = model_run_result[1] 
        print('ID is ', ID, ' device_super_name is ', device_super_name) 
        if count > 20:
            break  
    


def add_tag_to_recording(user_token, recordingId, json_data):
    url = parameters.server_endpoint + parameters.tags_url
    

    payload = "recordingId=" + recordingId + \
        "&tag=" \
        + json_data        
        
    headers = {
            'Content-Type': "application/x-www-form-urlencoded",
            'Authorization': user_token
            }

    response = requests.request("POST", url, data=payload, headers=headers)

    return response

def test_add_tag_to_recording():
    user_token = get_cacophony_user_token()
    version = '000003'
    tag = {}
    tag['animal'] = 'bigBirdzz'
    tag['startTime'] = 1
    tag['duration'] = 2
    tag['automatic'] = True
    tag['confidence'] = 0.9
    tag['confirmed'] = True
    tag['version'] = version
    json_tag = json.dumps(tag)
    resp = add_tag_to_recording(user_token, "158698", json_tag)
    print('resp is: ', resp.text)

def create_local_tags_from_model_run_result():
    # This will create tags on the local db for using the latest model_run_result
    # Only model_run_results with a probablility >= probability_cutoff_for_tag_creation will used
    cur = get_database_connection().cursor()

    sql = '''
        SELECT model_run_result.modelRunName, model_run_result.recording_id, model_run_result.startTime, model_run_result.duration, model_run_result.predictedByModel, model_run_result.probability, model_run_result.actual_confirmed, model_run_result.device_super_name, model_run_result.device_name 
        FROM model_run_result 
        WHERE probability >= ? AND modelRunName = ? AND predictedByModel = ? AND NOT EXISTS (SELECT *
                                                                                            FROM tags
                                                                                            WHERE tags.recording_Id = model_run_result.recording_id AND tags.startTime = model_run_result.startTime AND tags.what = model_run_result.predictedByModel AND tags.modelRunName = model_run_result.modelRunName AND tags.version = ?)
        '''
     

    cur.execute(sql, (probability_cutoff_for_tag_creation, model_run_name, predictedByModel_tag_to_create, model_version))  
   
    model_run_results = cur.fetchall()
    count_results = len(model_run_results)
    count_of_potential_tags = 0
    count_of_tags_created = 0
    for model_run_result in model_run_results:
        try:
            print("Processing ", count_of_potential_tags , " of ", count_results)
            count_of_potential_tags+=1
            modelRunName = model_run_result[0]
            recording_id = model_run_result[1]
            startTime = model_run_result[2]
            duration = model_run_result[3]
            predictedByModel = model_run_result[4] 
            probability = model_run_result[5] # probability
            actual_confirmed = model_run_result[6]
            device_super_name = model_run_result[7]
            device_name = model_run_result[8]    
              
            automatic = 'True'
            created_locally = 1 # 1 is true as using integer in db
            
            now = datetime.now(timezone('Zulu')) 
            fmt = "%Y-%m-%dT%H:%M:%S %Z"
            createdAtDate = now.strftime(fmt)
                  
            confirmed_by_human = 0 # using 0 is false in db
            # If actual_confirmed is NOT NULL, then only create a tag if actual_confirmed == predictedByModel
            if actual_confirmed:
                if actual_confirmed != predictedByModel:
                    print("The model predicted ", predictedByModel, " but the actual_confirmed is ", actual_confirmed, " so a tag will NOT be created")

                    continue # Don't create tag if actual_confirmed is not the same as predicted (I'm not tempted to upload actual_confirmed, as this would make model look better than it is)
                else:
                    count_of_tags_created +=1
                    print('Inserting tag ', count_of_tags_created, ' for: ', recording_id, ' ', predictedByModel)
                    confirmed_by_human = 1                 
            
            cur1 = get_database_connection().cursor()
           
            sql = ''' INSERT INTO tags(modelRunName, recording_id, startTime, duration, what, confidence, device_super_name, device_name, version, automatic, confirmed_by_human, created_locally, createdAt, tagger_username)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) '''
            cur1.execute(sql, (modelRunName, recording_id, startTime, duration, predictedByModel, probability, device_super_name, device_name, model_version, automatic, confirmed_by_human, created_locally, createdAtDate, cacophony_user_name))
            
            get_database_connection().commit()
        except Exception as e:
            print(e, '\n')
            print('Error processing modelRunName ', modelRunName)
        
    print('Finished processing ', count_of_potential_tags, ' potential tags in local database')
    print(count_of_tags_created, ' tags were inserted into the local database.  You can now upload them to the Cacophony server.')

def update_device_name_onsets_when_missing():
    cur = get_database_connection().cursor()
    cur.execute("SELECT ID, recording_id FROM onsets WHERE device_name IS NULL")  
    onsets_with_null_device_name = cur.fetchall()
    count = 0
    for onset_with_null_device_name in onsets_with_null_device_name:
        count+=1
        print('Updating ', count, ' of ', len(onsets_with_null_device_name))
        ID = onset_with_null_device_name[0]
        recording_id = onset_with_null_device_name[1]
        
        cur1 = get_database_connection().cursor()
        cur1.execute("SELECT device_name FROM recordings WHERE recording_id = ?", (recording_id,)) 
        rows = cur1.fetchall() 
        device_name = rows[0][0]
        
        cur2 = get_database_connection().cursor()                
        cur2.execute("UPDATE onsets SET device_name = ? WHERE ID = ?", (device_name, ID))  
                
        get_database_connection().commit()
        
def update_device_name_model_run_result_when_missing():
    cur = get_database_connection().cursor()
    cur.execute("SELECT ID, recording_id FROM model_run_result WHERE device_name IS NULL")  
    onsets_with_null_device_name = cur.fetchall()
    count = 0
    for onset_with_null_device_name in onsets_with_null_device_name:
        count+=1
        print('Updating ', count, ' of ', len(onsets_with_null_device_name))
        ID = onset_with_null_device_name[0]
        recording_id = onset_with_null_device_name[1]
        
        cur1 = get_database_connection().cursor()
        cur1.execute("SELECT device_name FROM recordings WHERE recording_id = ?", (recording_id,)) 
        rows = cur1.fetchall() 
        device_name = rows[0][0]
        
        cur2 = get_database_connection().cursor()                
        cur2.execute("UPDATE model_run_result SET device_name = ? WHERE ID = ?", (device_name, ID))  
                
        get_database_connection().commit()   
    print('Finished updating model_run_result device_names') 

def upload_tags_for_all_locations_to_cacophony_server():
    print("About to upload ALL tags to Cacophony Server")
    
    sql = '''select distinct device_super_name from tags'''
    cur = get_database_connection().cursor()  
    cur.execute(sql) 
    rows = cur.fetchall() 
    for row in rows:        
        device_super_name = row[0]
        upload_tags_to_cacophony_server(device_super_name)

def upload_tags_to_cacophony_server(location_filter):
    print("About to upload tags to Cacophony Server")
    user_token = get_cacophony_user_token()
    cur = get_database_connection().cursor()
    
    if location_filter !='not_used':
        cur.execute("SELECT ID, recording_id, startTime, duration, what, automatic, confidence, confirmed_by_human, modelRunName, version FROM tags WHERE modelRunName = ? AND (copied_to_server IS NULL OR copied_to_server = 0) AND device_super_name = ?", (model_run_name, location_filter))   
    else:            
        cur.execute("SELECT ID, recording_id, startTime, duration, what, automatic, confidence, confirmed_by_human, modelRunName, version FROM tags WHERE modelRunName = ? AND (copied_to_server IS NULL OR copied_to_server = 0)", (model_run_name,))   
    
    tags_to_send_to_server = cur.fetchall()
    count_of_tags_to_send_to_server = len(tags_to_send_to_server)
    
    if count_of_tags_to_send_to_server < 1:
        print('There are no tags to process :-(')
        return 
    
    count = 0
    for tag_to_send_to_server in tags_to_send_to_server:
        try:
            count+=1
            print('Processing ', count, ' of ', count_of_tags_to_send_to_server)
            ID = tag_to_send_to_server[0]
            recording_id = tag_to_send_to_server[1]
            recording_id_str = str(recording_id)
            startTime = tag_to_send_to_server[2]
            duration = tag_to_send_to_server[3]
            what = tag_to_send_to_server[4]
            automatic_str = tag_to_send_to_server[5]
            
            automatic_bool = (automatic_str == 'True')
            confidence = tag_to_send_to_server[6]
            confirmed_by_human_int = tag_to_send_to_server[7]
            confirmed_by_human_bool = bool(confirmed_by_human_int)
            

                
            tag = {}
            tag['what'] = what
            tag['startTime'] = str(startTime)
            tag['duration'] = str(duration)
            tag['automatic'] = automatic_bool
            tag['confidence'] = str(confidence)
            tag['confirmed'] = confirmed_by_human_bool
            tag['version'] = str(version)
            json_tag = json.dumps(tag)

            resp = add_tag_to_recording(user_token, recording_id_str, json_tag)
            resp_dict = json.loads(resp.text)
            
            cur2 = get_database_connection().cursor()  
            
            print('Going to update tags table for recording: ', recording_id_str, ' startTime: ', startTime, ' at ', location_filter, ' with a ', what)
                          
            if resp.ok:                
                success = resp_dict['success']
                print('success is: ', success)
                if success:
                    
                    cur2.execute("UPDATE tags SET copied_to_server = ? WHERE ID = ?", (1, ID)) 
                     
                else:
                    print('Error processing ', recording_id_str, ' ', resp.text)
                    cur2.execute("UPDATE tags SET copied_to_server = ? WHERE ID = ?", (-1, ID))
                
            else:
                error_message = resp_dict['message']
                print('Server returned the error: ', error_message)
                cur2.execute("UPDATE tags SET copied_to_server = ? WHERE ID = ?", (-1, ID))
                
            get_database_connection().commit() 
        
        except Exception as e:
            print(e, '\n')
            print('Error processing tag ', recording_id_str,  ' ', resp.text)


def update_model_run_results_with_onsets_used_to_create_model(model_run_name, csv_filename):
    print(model_run_name)   
    print("\n")   
    print(csv_filename)   
    
    # Extract onsets from csv file.
    with open(csv_filename) as fp:
        line = fp.readline()        
        while line:
          
            lineParts = line.split(',')
            recording_id = lineParts[1]
            start_time = lineParts[2]
            print('recording id is ', recording_id, '\n')
            print('start time is ', start_time, '\n\n')
            
            # now update model_run_result
            cur = get_database_connection().cursor()                
            cur.execute("UPDATE model_run_result SET used_to_create_model = 1 WHERE modelRunName = ? AND recording_id = ? AND startTime = ?", (model_run_name, recording_id, start_time))  
                                    
            get_database_connection().commit()  
                
            line = fp.readline()
            
    print("Finished updating model run result table") 



def add_device_names_to_arff():
    input_filename = 'arff_file_for_weka_model_creation_image_filtered.arff'
    input_filename_path = parameters.base_folder + '/' + parameters.run_folder + '/' + input_filename
    
    if not os.path.isfile(input_filename_path):
        print(input_filename_path + ' does not exist - stopping')
    
    
    output_filename_path = parameters.base_folder + '/' + parameters.run_folder + '/device_names_added_' + input_filename
    # Get list of unique 
    cur = get_database_connection().cursor()    
    cur.execute("select distinct device_super_name from model_run_result where modelRunName = ?", (model_run_name,))      
    device_super_names = cur.fetchall()
    numberOfSuperNames = len(device_super_names)
    print('numberOfSuperNames ', numberOfSuperNames)
    
    device_super_names_str = ''
    print(device_super_names_str)
    
    count = 0
    for device_super_name in device_super_names:  
        count+=1    
        print(device_super_name[0])  
        device_super_names_str+= device_super_name[0]
        if count < numberOfSuperNames: # Do not want a comma at the end of the string for arff format
            device_super_names_str+= ', '
   
    print(device_super_names_str)
    
    print('input_filename_path ', input_filename_path)
    print('output_filename_path ', output_filename_path)
    
    f_output_filename_path=open(output_filename_path,'w+')
    
    with open(input_filename_path) as fp:
        line = fp.readline()
        data_found = False 
        first_attribute_found = False       
        while line:
            # First need to add the extra @attribute definition
            if not first_attribute_found:
                if line.startswith('@attribute'):
                    first_attribute_found = True
                    # Add in the new attribute description
#                     f_output_filename_path.write('@attribute deviceName { sunny, overcast }\n')
                    f_output_filename_path.write('@attribute deviceName { ' + device_super_names_str +' }\n')
            
            if not data_found:
                if line.startswith('@data'):
                    data_found = TRUE
#                     continue # data will start on next line
                f_output_filename_path.write(line)
            else:
                # Need to find the device name for this recording id
                line_parts = line.split('$')
                recording_id = line_parts[1]
                
                cur2 = get_database_connection().cursor()    
                cur2.execute("select distinct device_super_name from recordings where recording_id = ?", (recording_id,))      
                device_super_name = cur2.fetchall()
                print('device_super_name', device_super_name[0][0])
                
                print('recording_id ', recording_id)
#                 f_output_filename_path.write('adeviceName,' + line)
                f_output_filename_path.write(device_super_name[0][0] + ',' + line)
                
            print(line)
            line = fp.readline()
            
    f_output_filename_path.close()    
            
   

def create_input_arff_file_for_single_onset_prediction(output_filename_path, device_super_name_for_this_onset):
    
    f_output_filename_path=open(output_filename_path,'w+')
    f_output_filename_path.write('@relation morepork_more-pork_vs\n')
    f_output_filename_path.write('@attribute filename string\n')
    
    # Add in the device super names attribute
    # Get list of unique 
    cur = get_database_connection().cursor()    
    cur.execute("select distinct device_super_name from recordings")      
    device_super_names = cur.fetchall()
    numberOfSuperNames = len(device_super_names)
#     print('numberOfSuperNames ', numberOfSuperNames)
    
    device_super_names_str = ''
#     print(device_super_names_str)
    
    count = 0
    for device_super_name in device_super_names:  
        count+=1    
#         print(device_super_name[0])  
        device_super_names_str+= device_super_name[0]
        if count < numberOfSuperNames: # Do not want a comma at the end of the string for arff format
            device_super_names_str+= ', '
   
#     print(device_super_names_str)
    f_output_filename_path.write('@attribute deviceSuperName {' + device_super_names_str +'}' + '\r\n')
    
    f_output_filename_path.write('@attribute class {' + class_names +'}' + '\r\n')
    f_output_filename_path.write('@data' + '\r\n')  
    f_output_filename_path.write('input_image.jpg,' + device_super_name_for_this_onset + ',unknown' + '\r\n')       
    
    f_output_filename_path.close()


def update_onsets_with_datetime():
    cur = get_database_connection().cursor()
    cur.execute("select ID, recording_id from onsets where recordingDateTime IS NULL")      
    onsets = cur.fetchall()
    numOfOnsets = len(onsets)
    count = 0
    
    for onset in onsets:
        print('Processing ' + str(count) + ' of ' + str(numOfOnsets))
        ID = onset[0]
        recording_id = onset[1]
        print(str(ID) + " " + str(recording_id))
        cur.execute("select recordingDateTime from recordings where recording_id = ?", (recording_id,)) 
        recordingDateTime_results = cur.fetchall()
        recordingDateTime = recordingDateTime_results[0][0]
        print(recordingDateTime)
        
        sql = ''' UPDATE onsets
                SET recordingDateTime = ?               
                WHERE ID = ?'''
        
        cur.execute(sql, (recordingDateTime, ID))
        count+=1
        get_database_connection().commit() 
    

             
        
def find_suitable_probability_cutoff():
    cur = get_database_connection().cursor()
    
    sql = '''
    select device_super_name, device_name, probability, used_to_create_model, recording_id, startTime, predictedByModel, actual_confirmed,  strftime('%m', recordingDateTime) as month, strftime('%Y', recordingDateTime) as year
    from model_run_result
    where modelRunName = '2020_02_08_1' and actual_confirmed is not null
    order by probability DESC
    '''
    
    
    cur.execute(sql)      
    model_run_results = cur.fetchall()
    model_run_result = len(model_run_results)
#     count = 0
    
    for model_run_result in model_run_results:
        device_super_name = model_run_result[0]
        device_name = model_run_result[1]
        probability = model_run_result[2]
        used_to_create_model = model_run_result[3]
        recording_id = model_run_result[4]
        startTime = model_run_result[5]
        predictedByModel = model_run_result[6]
        actual_confirmed = model_run_result[7]
        month = model_run_result[8]
        year = model_run_result[9]
        print(device_super_name, " ", device_name, " ", probability, " ", used_to_create_model, " ", recording_id, " ", startTime , " ",predictedByModel, " ", actual_confirmed , " ",month , " ", year)
      

def convert_time_zones(day_time_from_database):
    # recording ID is  319810 - server says time is Thu Jun 13 2019, 06:42:00
#     day_time_from_database = '2019-06-12T18:42:00.000Z'
    day_time_from_database_00_format = datetime.fromisoformat(day_time_from_database.replace('Z', '+00:00'))
    print('day_time_from_database_00_format: ', day_time_from_database_00_format)
    nz = timezone('NZ')
    day_time_nz = day_time_from_database_00_format.astimezone(nz)
    print('day_time_nz: ', day_time_nz)
    return day_time_nz
    
def update_table_with_NZ_time():
    table_name = 'recordings'
    
    cur = get_database_connection().cursor()
    cur.execute("select ID, recordingDateTime from " + table_name + " where recordingDateTimeNZ IS NULL")      
    records = cur.fetchall()
    numOfRecords = len(records)
    count = 0
    
    for record in records:
        try:        
        
            ID = record[0]
            recordingDateTime = record[1]
            
            print('Processing ID ' + str(ID) + " which is " + str(count) + ' of ' + str(numOfRecords))
            
            recordingDateTimeNZ = convert_time_zones(recordingDateTime)
            
            sql = ''' UPDATE ''' + table_name + ''' 
                    SET recordingDateTimeNZ = ?               
                    WHERE ID = ?'''
            
            cur.execute(sql, (recordingDateTimeNZ, ID))
            count+=1
            get_database_connection().commit() 
            
        except Exception as e:
            print(str(e))
            print("Error processing ID " + str(ID))
        
def test_not_between_dates(firstDateStr, lastDateStr):
    table_name = 'onsets'
    
    firstDateStr = firstDateStr + ':00:00:00'
    lastDateStr = lastDateStr + ':23:59:59'
    
    cur = get_database_connection().cursor()
    # https://stackoverflow.com/questions/8187288/sql-select-between-dates
    cur.execute("select ID, recordingDateTime from " + table_name + " where strftime('%Y-%m-%d:%H-%M-%S', recordingDateTimeNZ) NOT BETWEEN '" + firstDateStr + "' AND '" + lastDateStr + "' order by recordingDateTimeNZ")      
         
    records = cur.fetchall()
    numOfRecords = len(records)
    count = 0
    
    for record in records:          
        
        ID = record[0]
        recordingDateTime = record[1]
        
        print('Processing ID ' + str(ID) + " which is " + str(count) + ' of ' + str(numOfRecords) + ' ' + recordingDateTime)
       
def get_recording_position_in_seconds(x_mouse_pos, x_scroll_bar_minimum, x_scroll_bar_maximum, canvas_width, recording_length):
    recording_pos_seconds = (((x_mouse_pos/canvas_width) * (x_scroll_bar_maximum - x_scroll_bar_minimum)) + x_scroll_bar_minimum) * recording_length
    print("x clicked at ", recording_pos_seconds, ' seconds')
    return round(recording_pos_seconds,1)

def get_recording_position_in_hertz(y_mouse_pos, canvas_height, recording_minimum_freq, recording_maximum_freq):
    recording_pos_hertz = recording_maximum_freq - ((y_mouse_pos/canvas_height) * (recording_maximum_freq - recording_minimum_freq))
    return int(recording_pos_hertz)    

def get_spectrogram_clicked_at_y_percent(y_mouse_pos,canvas_height):
    return y_mouse_pos/canvas_height

def spectrogram_clicked_at_x_percent(x_mouse_pos, x_scroll_bar_minimum, x_scroll_bar_maximum, canvas_width):
    x_position_percent = (((x_mouse_pos/canvas_width) * (x_scroll_bar_maximum - x_scroll_bar_minimum)) + x_scroll_bar_minimum)
#     print("x_position_percent ", x_position_percent)
    return x_position_percent

def convert_event_x_pos_to_canvas_x_pos(event_x):
    return event_x

def convert_pos_in_secs_to_canvas_pos2(recording_pos_seconds, recording_length, x_scroll_bar_minimum, x_scroll_bar_maximum, canvas_width):
    print("recording_pos_seconds ", recording_pos_seconds)
    print("x_scroll_bar_minimum ", x_scroll_bar_minimum)
    print("x_scroll_bar_maximum ", x_scroll_bar_maximum)
    print("canvas_width ", canvas_width)
    
    recording_pos_seconds_div_recording_length = recording_pos_seconds/recording_length
    print("recording_pos_seconds_div_recording_length ", recording_pos_seconds_div_recording_length)
    recording_pos_seconds_div_recording_length_minus_x_scroll_bar_minimum = recording_pos_seconds_div_recording_length - x_scroll_bar_minimum
    print("recording_pos_seconds_div_recording_length_minus_x_scroll_bar_minimum ", recording_pos_seconds_div_recording_length_minus_x_scroll_bar_minimum) 
    x_scroll_bar_maximum_minus_x_scroll_bar_minimum = x_scroll_bar_maximum-x_scroll_bar_minimum
    print("x_scroll_bar_maximum_minus_x_scroll_bar_minimum ", x_scroll_bar_maximum_minus_x_scroll_bar_minimum) 
    result = ((recording_pos_seconds_div_recording_length_minus_x_scroll_bar_minimum)*x_scroll_bar_maximum_minus_x_scroll_bar_minimum)* canvas_width
    print("result ", result)
    
    x_mouse_pos = (((recording_pos_seconds/recording_length)-x_scroll_bar_minimum)*(x_scroll_bar_maximum-x_scroll_bar_minimum))*canvas_width
    return x_mouse_pos

def convert_time_in_seconds_to_x_value_for_canvas_create_method(start_time_seconds, duration, spectrogram_image_width):
    return  ((start_time_seconds/duration) * spectrogram_image_width)  

def convert_frequency_to_y_value_for_canvas_create_method(spectrogram_image_min_freq, spectrogram_image_max_freq, freq_to_convert, spectrogram_image_height):    
    frequency_range = spectrogram_image_max_freq - spectrogram_image_min_freq
    how_far_from_top_of_freq_range = spectrogram_image_max_freq - freq_to_convert   
    result =  (how_far_from_top_of_freq_range/frequency_range)*spectrogram_image_height    
    return  result    

def convert_pos_in_percent_to_position_in_seconds(pos_in_percent, duration):
    return duration * pos_in_percent
    
def convert_pos_in_seconds_to_position_in_percent(pos_in_seconds, duration):
    return pos_in_seconds / duration
    
def convert_pos_in_seconds_to_canvas_position(spectrogram_image_width, pos_in_seconds, duration):
    pos_in_percent = convert_pos_in_seconds_to_position_in_percent(pos_in_seconds, duration)
    return spectrogram_image_width * pos_in_percent

def convert_frequency_to_vertical_position_on_spectrogram(spectrogram_image_height, frequency, spectrogram_start_frequency, spectrogram_finish_frequency):
    return spectrogram_image_height - (spectrogram_image_height*frequency/(spectrogram_finish_frequency - spectrogram_start_frequency))
        
def convert_x_or_y_postion_percent_to_x_or_y_spectrogram_image_postion(spectrogram_image_width_or_height, x_or_y_postion_percent):
    return spectrogram_image_width_or_height * x_or_y_postion_percent
    
def save_spectrogram_selection(selection_to_save):
    print("selection_to_save ", selection_to_save)
    
def insert_test_data_into_database(recording_id, start_time_seconds, finish_time_seconds, lower_freq_hertz, upper_freq_hertz, what ):    
    
    cur1 = get_database_connection().cursor()
    cur1.execute("SELECT device_super_name, device_name, recordingDateTime, recordingDateTimeNZ FROM recordings WHERE recording_id = ?", (recording_id,)) 
    rows = cur1.fetchall() 
    device_super_name = rows[0][0]  
    device_name = rows[0][1]
    recordingDateTime = rows[0][2]  
    recordingDateTimeNZ = rows[0][3] 
    
    try:     
        sql = ''' INSERT INTO test_data(recording_id, start_time_seconds, finish_time_seconds, lower_freq_hertz, upper_freq_hertz, what, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ)
                  VALUES(?,?,?,?,?,?,?,?,?,?) '''
        cur2 = get_database_connection().cursor()
        cur2.execute(sql, (recording_id, start_time_seconds, finish_time_seconds, lower_freq_hertz, upper_freq_hertz, what, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ ))
        get_database_connection().commit()
        return True
    except Exception as e:
        print(e, '\n')
        print('\t\tUnable to insert test_data ' + str(recording_id), '\n')   
        return False   
    
 
def delete_test_data_row(recording_id, start_time_seconds, finish_time_seconds, lower_freq_hertz, upper_freq_hertz, what): 
    
    cur3 = get_database_connection().cursor()
    sql = 'DELETE FROM test_data WHERE recording_id=? and start_time_seconds=? and finish_time_seconds=? and lower_freq_hertz=? and upper_freq_hertz=? and what=?'
    cur3.execute(sql, (recording_id, start_time_seconds, finish_time_seconds, lower_freq_hertz, upper_freq_hertz, what))
    get_database_connection().commit()
    
def retrieve_test_data_from_database(recording_id):
    
    cur = get_database_connection().cursor()
    cur.execute("SELECT recording_id, start_time_seconds, finish_time_seconds, lower_freq_hertz, upper_freq_hertz, what from test_data WHERE recording_id = ?", (recording_id,)) 
    test_data_rows = cur.fetchall() 
    return test_data_rows
    
def retrieve_recordings_for_creating_test_data(what_filter):
    table_name = 'recordings'
    
    firstDate = recordings_for_creating_test_data_start_date 
    lastDate = recordings_for_creating_test_data_end_date 
    
    cur = get_database_connection().cursor()
    # https://stackoverflow.com/questions/8187288/sql-select-between-dates

    if what_filter is None:
        cur.execute("select recording_id, datetime(recordingDateTime,'localtime') as recordingDateTimeNZ, device_name, duration, device_super_name from " + table_name + " where nightRecording = 'true' and recordingDateTimeNZ BETWEEN '" + firstDate + "' AND '" + lastDate + "' order by recording_id ASC")
    else:
        cur.execute("select recording_id, datetime(recordingDateTime,'localtime') as recordingDateTimeNZ, device_name, duration, device_super_name from " + table_name + " where nightRecording = 'true' and recordingDateTimeNZ BETWEEN '" + firstDate + "' AND '" + lastDate + "' and recording_id NOT IN (SELECT recording_id FROM test_data_recording_analysis WHERE recording_id = recording_id and what = '" + what_filter + "') order by recording_id ASC") 
               
    records = cur.fetchall()
                  
    return records

def retrieve_recordings_for_evaluating_test_validation_data(include_all_test_validation_recordings, include_recordings_with_model_predictions, include_recordings_that_have_been_manually_analysed, model_must_predict_what, probability_cutoff):
    
    table_name = 'recordings'
   
    firstDate = recordings_for_creating_test_data_start_date 
    lastDate = recordings_for_creating_test_data_end_date 
    
    probability_cutoff_float = float(probability_cutoff)
    
    sqlBuilding = "select recording_id, datetime(recordingDateTime,'localtime') as recordingDateTimeNZ, device_name, duration, device_super_name from " + table_name + " where nightRecording = 'true' and recordingDateTimeNZ BETWEEN '" + firstDate + "' AND '" + lastDate + "'"
        
    if not include_all_test_validation_recordings:        
    
        if include_recordings_with_model_predictions:
            if probability_cutoff_float == 0:
                sqlBuilding += " AND recording_id IN (SELECT recording_id FROM model_run_result WHERE modelRunName = '" + model_run_name + "' AND predictedByModel = '" + model_must_predict_what + "')"
            else:
                sqlBuilding += " AND recording_id IN (SELECT recording_id FROM model_run_result WHERE modelRunName = '" + model_run_name + "' AND predictedByModel = '" + model_must_predict_what + "' AND probability > " + probability_cutoff + ")"
           
                
        if include_recordings_that_have_been_manually_analysed:
            sqlBuilding += " AND recording_id IN (SELECT recording_id FROM test_data)"       
            
    sqlBuilding += " ORDER BY recording_id ASC"    
       
    print("The sql is: ", sqlBuilding)
    cur = get_database_connection().cursor()
    cur.execute(sqlBuilding)

    rows = cur.fetchall()
    return rows
    
def retrieve_recordings_except_test_validation_data(model_must_predict_what):   
    table_name = 'recordings'
   
    firstDateOfTestValidationDataToExclude = recordings_for_creating_test_data_start_date 
    lastDateOfTestValidationDataToExclude = recordings_for_creating_test_data_end_date 
    
    sqlBuilding = "select recording_id, datetime(recordingDateTime,'localtime') as recordingDateTimeNZ, device_name, duration, device_super_name from " + table_name + " where nightRecording = 'true' AND (recordingDateTimeNZ < '" + firstDateOfTestValidationDataToExclude + "' OR recordingDateTimeNZ > '" + lastDateOfTestValidationDataToExclude + "')"
    sqlBuilding += " AND recording_id IN (SELECT recording_id FROM model_run_result WHERE modelRunName = '" + model_run_name + "' AND predictedByModel = '" + model_must_predict_what + "')"
    
    sqlBuilding += " ORDER BY recording_id ASC" 
    
    print("sqlBuilding ", sqlBuilding)
    
    cur = get_database_connection().cursor()
    cur.execute(sqlBuilding)
    rows = cur.fetchall()
    
    return rows     
   
def mark_recording_as_analysed(recording_id, what):
    try: 
        
        if has_this_recording_been_analysed_for_this(recording_id, what):
            # No need to try to insert data as it is already in database (and there is a unique constraint)
            return True 
                
        cur = get_database_connection().cursor()
        sql = ''' INSERT INTO test_data_recording_analysis(recording_id, what)
                      VALUES(?,?) '''
        cur.execute(sql, (recording_id, what))
        get_database_connection().commit()   
        return True
    except Exception as e:
        print(e, '\n')
        print('\t\tUnable to insert test_data_recording_analysis ' + str(recording_id), '\n')  
        return False   
    
def has_this_recording_been_analysed_for_this(recording_id, what_to_filter_on):
    try: 
        cur = get_database_connection().cursor()
        cur.execute("SELECT ID FROM test_data_recording_analysis WHERE recording_id = ? and what = ?", (recording_id, what_to_filter_on))
        record = cur.fetchone()             # https://stackoverflow.com/questions/2440147/how-to-check-the-existence-of-a-row-in-sqlite-with-python
        
        if record is None:
            return False
        else:
            return True
        
    except Exception as e:
        print(e, '\n')

def get_spectrogram_rectangle_selection_colour(what):
    # http://www.science.smith.edu/dftwiki/index.php/Color_Charts_for_TKinter
    switcher = {
        "morepork_more-pork": "green",
        "maybe_morepork_more-pork":"yellow",
        "morepork_more-pork_part":"blue",
        "cow": "dark orange"        
    }
    return switcher.get(what, "red")
    
def get_model_predictions(recording_id):
    table_name = 'model_run_result'        
    
    cur = get_database_connection().cursor()    

    cur.execute("select startTime, duration, predictedByModel, probability, actual_confirmed from " + table_name + " where recording_id = ? and modelRunName = ?", (recording_id, model_run_name) )
   
    records = cur.fetchall()
                  
    return records


def create_features_for_onsets():
    cur = get_database_connection().cursor()    

    # First do the onsets that have been confirmed
    cur.execute("select ID, recording_id, start_time_seconds, actual_confirmed, device_super_name, device_name, duration_seconds, recordingDateTime FROM ONSETs WHERE version = ? AND actual_confirmed IS NOT NULL AND NOT EXISTS (SELECT onset_id FROM features WHERE onsets.recording_id = features.recording_id AND onsets.start_time_seconds = features.start_time_seconds) ORDER BY recording_id DESC", (str(onset_version)) )
        
    records = cur.fetchall()
    process_onset_features(records, True)
        
    # Now to the rest of the onsets
    cur.execute("select ID, recording_id, start_time_seconds, actual_confirmed, device_super_name, device_name, duration_seconds, recordingDateTime FROM ONSETs WHERE version = ? AND actual_confirmed IS NULL AND NOT EXISTS (SELECT onset_id FROM features WHERE onsets.recording_id = features.recording_id AND onsets.start_time_seconds = features.start_time_seconds) ORDER BY recording_id DESC", (str(onset_version)))
    
    records = cur.fetchall()
    process_onset_features(records, False)

        
def process_onset_features(records, confirmed):
    number_of_records = len(records)
    
    count = 0
    
    previous_recording_id = -1 # Only going to read recording from file once - ie if it has changed since last row result
    y_filtered = None
    sr = None
    for record in records:
        count+=1
        if confirmed:
            print(count, " of (confirmed) ", number_of_records)
        else:
            print(count, " of (not confirmed) ", number_of_records)
            
        recording_id = record[1]
        if recording_id != previous_recording_id:
            print("recording_id to process changed from ", previous_recording_id, " to ", recording_id)
            y_filtered, sr  = get_filtered_recording(recording_id)            
            
        create_features_for_single_onset_version_2(record[0], recording_id, record[2], record[3], record[4], record[5], record[6], record[7], y_filtered, sr)
        previous_recording_id = recording_id
    

def get_filtered_recording(recording_id):
    recordings_folder_with_path = base_folder + '/' + downloaded_recordings_folder
    filename = str(recording_id) + ".m4a"
    audio_in_path = recordings_folder_with_path + "/" + filename
    y, sr = librosa.load(audio_in_path)
    y_filtered = apply_band_pass_filter(y, sr)
    return y_filtered, sr
             
def create_features_for_single_onset_version_2(onset_id, recording_id, start_time_seconds, actual_confirmed, device_super_name, device_name, duration_seconds, recordingDateTime, y_filtered, sr):
    
    start_time_seconds_float = float(start_time_seconds)   
         
    try:
        
        start_position_array = int(sr * start_time_seconds_float)              
                   
        end_position_array = start_position_array + int((sr * 1.0))                  
                    
        y_part = y_filtered[start_position_array:end_position_array]  
                
        rms = librosa.feature.rms(y=y_part)
        
        spectral_centroid = librosa.feature.spectral_centroid(y=y_part, sr=sr)
        
        spectral_bandwidth = librosa.feature.spectral_bandwidth(y=y_part, sr=sr)
        
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y_part, sr=sr)
        
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y_part)  
        
        number_of_frames = rms.shape[1]
        

        print("number_of_frames ", number_of_frames)

        sqlBuilding = "INSERT INTO features (onset_id, recording_id, start_time_seconds, actual_confirmed, device_super_name, device_name, duration_seconds, recordingDateTime"
        for i in range(number_of_frames):
            sqlBuilding += ", rms" + str(i) 
            
        for i in range(number_of_frames):
            sqlBuilding += ", spectral_centroid" + str(i)
            
        for i in range(number_of_frames):
            sqlBuilding += ", spectral_bandwidth" + str(i)
            
        for i in range(number_of_frames):
            sqlBuilding += ", spectral_rolloff" + str(i)
            
        for i in range(number_of_frames):
            sqlBuilding += ", zero_crossing_rate" + str(i)
        
        
        sqlBuilding += ")"
        sqlBuilding += " VALUES("
        
        sqlBuilding += str(onset_id) + ","
        sqlBuilding += str(recording_id) + ","
        sqlBuilding += str(start_time_seconds) + ","
        sqlBuilding += "'" + str(actual_confirmed) + "'" + ","
        
        sqlBuilding += "'" + str(device_super_name) + "'" + ","
        sqlBuilding += "'" + str(device_name) + "'" + ","
        sqlBuilding += str(duration_seconds) + ","
        sqlBuilding += "'" + str(recordingDateTime) + "'"
        
        for i in range(number_of_frames):
            sqlBuilding += "," + "'" + str(rms[0][i]) + "'"
         
        for i in range(number_of_frames):
            sqlBuilding += "," + "'" + str(spectral_centroid[0][i]) + "'"
            
        for i in range(number_of_frames):
            sqlBuilding += "," + "'" + str(spectral_bandwidth[0][i]) + "'"
            
        for i in range(number_of_frames):
            sqlBuilding += "," + "'" + str(spectral_rolloff[0][i]) + "'"
            
        for i in range(number_of_frames):
            sqlBuilding += "," + "'" + str(zero_crossing_rate[0][i]) + "'"
            
        sqlBuilding += ")"        

        
        cur = get_database_connection().cursor()
        cur.execute(sqlBuilding)
        get_database_connection().commit()        

    except Exception as e:
        print(e)
      
# def copy_actual_confirmed_onset_5_to_onset_6():
#     cur = get_database_connection().cursor()
#     cur.execute("SELECT actual_confirmed, recording_id, start_time_seconds from onsets WHERE version = 5 AND actual_confirmed IS NOT NULL")
#     records = cur.fetchall()
#     for record in records:
#         print(record)
#         cur.execute("UPDATE onsets SET actual_confirmed = ? WHERE actual_confirmed IS NULL AND version = 6 AND recording_id = ? AND start_time_seconds = ?", (record[0], record[1], record[2]) )
#         get_database_connection().commit() 
#         
#     print("Finished")
#     
# def update_ver_6_onsets_with_ver_5():
#     cur = get_database_connection().cursor()
# #     cur.execute("SELECT * from onsets WHERE version = 5")
# #     records_ver_5 = cur.fetchall()
# #     print("Number of records is ", len(records_ver_5))
# #     for record_ver_5 in records_ver_5:        
# #         print(record_ver_5)
# #         recording_id = record_ver_5[2]
# #         print(recording_id)
# #         
# #         start_time_seconds = record_ver_5[3]
# #         print(start_time_seconds)
#         
#         
#     cur.execute("SELECT * from onsets WHERE version = 6 AND MPEG7_Edge_Histogram0 IS NULL")
#     records_ver_6 = cur.fetchall()
#     for record_ver_6 in records_ver_6:
#         print(record_ver_6)
#         recording_id_ver_6 = record_ver_6[2]
#         print(recording_id_ver_6)
#         start_time_seconds = record_ver_6[3]
#         print(start_time_seconds)
#         
#         cur.execute("SELECT * from onsets WHERE version = 5 AND recording_id = ? AND start_time_seconds = start_time_seconds", (recording_id_ver_6,))
#         records_ver_5 = cur.fetchall()
#         print("Number of records is ", len(records_ver_5))
#         for record_ver_5 in records_ver_5: 
#             print(record_ver_5)
#             cur.execute("UPDATE onsets SET actual_confirmed = ? WHERE actual_confirmed IS NULL AND version = 6 AND recording_id = ? AND start_time_seconds = ?", (record[0], record[1], record[2]) )
#             

def march_test_data_analysis():
    cur = get_database_connection().cursor()
    cur.execute("SELECT recording_id, start_time_seconds, finish_time_seconds from test_data WHERE what = 'morepork_more-pork'")
    test_data_records = cur.fetchall()
    number_of_test_data = len(test_data_records)
    print("Number of records is ", number_of_test_data)
    count_of_test_data_with_ver_5_onset = 0
    count_of_test_data_with_ver_6_onset = 0
    count_of_test_data_with_ver_7_onset = 0
    record_count = 0
    for test_data_record in test_data_records:  
        record_count +=1      
        print("Processing ", record_count, " of ", number_of_test_data, ": ", test_data_record)
        recording_id = test_data_record[0]
#         print(recording_id)
        test_data_start_time_seconds = test_data_record[1]
#         print(test_data_start_time_seconds)
        test_data_finish_time_seconds = test_data_record[2]
#         print(test_data_finish_time_seconds)
        
        cur.execute("SELECT recording_id, start_time_seconds, version from onsets WHERE recording_id = ? AND start_time_seconds > ? AND start_time_seconds < ?", (recording_id, test_data_start_time_seconds, test_data_finish_time_seconds))
        onset_records = cur.fetchall()
        for onset_record in onset_records:  
            recording_id = onset_record[0]
            start_time_seconds = onset_record[1]
            version = onset_record[2]
            print("recording_id = ", recording_id, " start_time_seconds = ", start_time_seconds," version = ", version," test_data_start_time_seconds = ", test_data_start_time_seconds," test_data_finish_time_seconds = ", test_data_finish_time_seconds)
            if version == '5':
                count_of_test_data_with_ver_5_onset += 1
            if version == '6':
                count_of_test_data_with_ver_6_onset += 1
            if version == '7':
                count_of_test_data_with_ver_7_onset += 1
       
    print(count_of_test_data_with_ver_5_onset, " of the test data had a version 5 onset")
    print(count_of_test_data_with_ver_6_onset, " of the test data had a version 6 onset")
    print(count_of_test_data_with_ver_7_onset, " of the test data had a version 7 onset")
    

def butter_bandpass(lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a


def butter_bandpass_filter(data, lowcut, highcut, fs, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = lfilter(b, a, data)
    return y




def paired_item(source):
    source_iter = iter(source)
    while True:
        try:
            yield next(source_iter).item(), next(source_iter).item()
        except StopIteration:
            return

def merge_paired_short_time(udarray, small_time):
    paired_iter = paired_item(udarray)
    r = None
    for s in paired_iter:
        if not r:
            r = s
        elif s[0] < r[1] + small_time:
            r = r[0], s[1]
        else:
            yield r
            r = s
    if r:
        yield r



class window_helper:
    cache = {}
  
#     def construct_window(self, width, family, scale):
    def construct_window(self,width, family, scale):
        if family == 'bartlett':
            return np.bartlett(width) * scale
  
        if family == 'blackman':
            return np.blackman(width) * scale
  
        if family == 'hamming':
            return np.hamming(width) * scale
  
        if family == 'hann':
            import scipy.signal
            return scipy.signal.hann(width) * scale
  
        if family == 'hanning':
            return np.hanning(width) * scale
  
        if family == 'kaiser':
            beta = 14
            return np.kaiser(width, beta) * scale
  
        if family == 'tukey':
            import scipy.signal
            return scipy.signal.tukey(width) * scale
  
        print('window family %s not supported' % family)
  

    def get_window(self, key):      
        if not key in self.cache:
                self.cache[key] = self.construct_window(*key)                
        return window_helper.cache[key]
    
def check_python_version():
    if sys.version_info[0] < 3:
        print('python version 2 not supported, try activate virtualenv or run setup.')
        sys.exit()

def get_window_const(width, family, scale=1.0):
    check_python_version()
    a_window_helper = window_helper()    
    return a_window_helper.get_window((width, family, scale))
    

class spectrogram_helper:
    def __init__(self, source_pad, spectrogram, stride, sample_rate):
        self.spectrogram = spectrogram
        (self.block_count, dct_width) = spectrogram.shape
        self.stride = stride
 
        window_c = get_window_const(dct_width, 'tukey')
 
        for index in range(self.block_count):
            block_index = index * stride
            block = source_pad[block_index:block_index + dct_width] * window_c
            dct = scipy.fft.dct(block)
            spectrogram[index] = dct
 
        self.buckets = []
        msw = 50 * sample_rate // stride
        max_spec_width = min(msw, self.block_count)
        division_count = max(int((self.block_count * 1.7) / max_spec_width), 1)
        for i in range(division_count):
            t0 = 0
            if i:
                t0 = (self.block_count - max_spec_width) * \
                    i // (division_count - 1)
            t1 = min(t0 + max_spec_width, self.block_count)
            self.buckets.append((t0, t1))
 
        self.currentBucket = -2
 
    def get_tolerance(self, index):
        qb = (index, index, index)
        q = min(self.buckets, key=lambda x: abs(x[0] + x[1] - 2 * index))
        if self.currentBucket != q:
            self.currentBucket = q
            (t0, t1) = q
            bin_medians = np.median(abs(self.spectrogram[t0:t1, ]), axis=0)
            self.tolerance = 4 * \
                np.convolve(bin_medians, np.ones(8) / 8)[4:-3]
 
        return self.tolerance

def noise_reduce_dct(source, sample_rate):
    original_sample_count = source.shape[0]
    dct_width = 2048

    trim_width = int(dct_width / 8)
    stride = dct_width - trim_width * 3

    block_count = (original_sample_count + stride - 1) // stride
    source_pad = np.pad(source, (stride, stride * 2), 'reflect')

    #print('Building spectrogram')
    spectrogram = np.empty((block_count, dct_width))

    sph = spectrogram_helper(source_pad, spectrogram, stride, sample_rate)

    # anything below bass_cut_off_freq requires specialised techniques
    bass_cut_off_freq = 100
    bass_cut_off_band = bass_cut_off_freq * 2 * dct_width // sample_rate

    spectrogram_trimmed = np.empty((block_count, dct_width))
    rms_tab = np.empty(block_count)

    for index in range(block_count):
        dct = spectrogram[index]

        mask = np.ones_like(dct)
        mask[:bass_cut_off_band] *= 0

        rms_tab[index] = rms(dct * mask)

        tolerance = sph.get_tolerance(index)
        for band in range(dct_width):
            if abs(dct[band]) < tolerance[band]:
                mask[band] *= 0.0

        maskCon = 10 * np.convolve(mask, np.ones(8) / 8)[4:-3]

        maskBin = np.where(maskCon > 0.1, 0, 1)
        spectrogram_trimmed[index] = maskBin

    rms_cutoff = np.median(rms_tab)

    result_pad = np.zeros_like(source_pad)
    for index in range(1, block_count - 1):
        dct = spectrogram[index]

        trim3 = spectrogram_trimmed[index - 1] * \
            spectrogram_trimmed[index] * spectrogram_trimmed[index + 1]
        dct *= (1 - trim3)

        if rms(dct) < rms_cutoff:
            continue  # too soft

#         rt = scipy.fftpack.idct(dct) / (dct_width * 2)
        rt = scipy.fft.idct(dct) / (dct_width * 2)

        block_index = index * stride
        result_pad[block_index + trim_width * 1:block_index + trim_width *
                   2] += rt[trim_width * 1:trim_width * 2] * np.linspace(0, 1, trim_width)
        result_pad[block_index +
                   trim_width *
                   2:block_index +
                   trim_width *
                   6] = rt[trim_width *
                           2:trim_width *
                           6]  # *numpy.linspace(1,1,stride8*4)
        result_pad[block_index + trim_width * 6:block_index + trim_width *
                   7] = rt[trim_width * 6:trim_width * 7] * np.linspace(1, 0, trim_width)

    result = result_pad[stride:stride + original_sample_count]
    return result

def noise_reduce(source, sample_rate):
    return noise_reduce_dct(source, sample_rate)

def test_onset_version_7():
    print(sys.version)        
    
    recording_id = "544238"
    filename = recording_id + ".m4a"
    recordings_folder_with_path = base_folder + '/' + downloaded_recordings_folder
    audio_in_path = recordings_folder_with_path + "/" + filename

    y, sr = librosa.load(audio_in_path)
    y = butter_bandpass_filter(y, 600, 1200, sr, order=6)    
    y = noise_reduce(y, sr)    

    squawks = find_squawk_location_secs_in_single_recording(y,sr)
    print(squawks)    
    insert_onset_list_into_db(recording_id, squawks)

def calculate_prediction_accuracy_rates():
    probability_cutoff_for_tag_creation = 0.7
    
    first_test_data_recording_id = 537910
    last_test_data_recording_id = 563200
    
    # First calculate True Positives
    cur = get_database_connection().cursor()
    cur.execute("SELECT recording_id, startTime, duration, predictedByModel from model_run_result WHERE predictedByModel = 'morepork_more-pork' AND modelRunName = ? AND probability > ? AND recording_id > ? AND recording_id < ? ORDER BY recording_id DESC", (model_run_name, probability_cutoff_for_tag_creation, first_test_data_recording_id, last_test_data_recording_id))
    model_predictions = cur.fetchall()
    number_of_predictions = len(model_predictions)
    print("There are ", number_of_predictions, " predictions")
    number_of_true_positves = 0
    number_of_false_positves = 0
    for model_prediction in model_predictions:
#         print(model_prediction)
        recording_id = model_prediction[0]
        prediction_startTime = model_prediction[1]
        duration = model_prediction[2]
        prediction_endTime = prediction_startTime + duration
        print("recording_id ",recording_id, "prediction_startTime ", prediction_startTime, "prediction_endTime ", prediction_endTime)
        
#         cur.execute("SELECT recording_id, start_time_seconds, finish_time_seconds FROM test_data WHERE recording_id = ? AND (what = 'morepork_more-pork' OR what = 'maybe_morepork_more-pork') AND ((start_time_seconds > ? AND start_time_seconds < ?) OR (finish_time_seconds > ? AND finish_time_seconds < ?))", (recording_id, startTime, endTime,  startTime, endTime))
        cur.execute("SELECT recording_id, start_time_seconds, finish_time_seconds FROM test_data WHERE recording_id = ? AND ((? >= start_time_seconds AND ? <= finish_time_seconds) OR (? >= start_time_seconds AND ? <= finish_time_seconds))", (recording_id, prediction_startTime, prediction_startTime, prediction_endTime, prediction_endTime))
        row = cur.fetchone()
#         rows = cur.fetchall()
#         for row in rows:
#             start_time_seconds = row[1]
#             finish_time_seconds = row[2]            
#             
#             print(recording_id, " Prediction: startTime", prediction_startTime, "endTime ", prediction_endTime, " -- test_data: start_time_seconds ", start_time_seconds, " finish_time_seconds ", finish_time_seconds  )
            
        
        
        if row == None:            
            number_of_false_positves += 1
        else:
            number_of_true_positves += 1
#             recording_id = row[0]
#             start_time_seconds = row[1]
#             finish_time_seconds = row[2]
#             print(recording_id, " Prediction: startTime", prediction_startTime, "endTime ", prediction_endTime, " -- test_data: start_time_seconds ",start_time_seconds, " finish_time_seconds ", finish_time_seconds  )
            
    print("number_of_false_positves is ", number_of_false_positves)
    print("number_of_true_positves is ", number_of_true_positves)
        
        
def do_rectangle_times_overlap(rectangle_1_start, rectangle_1_finish, rectangle_2_start, rectangle_2_finish):
    rectangle_1_width = rectangle_1_finish - rectangle_1_start
    rectangle_2_width = rectangle_2_finish - rectangle_2_start
    
    if rectangle_1_width >= rectangle_2_width:
        # Determine in rectangle 2 start OR finish within rectangle 1 start AND finish
        if (rectangle_2_start >= rectangle_1_start) and (rectangle_2_start <= rectangle_1_finish):
            return True
        if (rectangle_2_finish >= rectangle_1_start) and (rectangle_2_finish <= rectangle_1_finish):
            return True
    else:
        # rectangle_2_width > rectangle_1_width
        if (rectangle_1_start >= rectangle_2_start) and (rectangle_1_start <= rectangle_2_finish):
            return True
        if (rectangle_1_finish >= rectangle_2_start) and (rectangle_1_finish <= rectangle_2_finish):
            return True
        
    return False
    
    

# def update_model_run_result_actual_confirmed_from_test_data():
#     # This is going to look at all the (morepork) model predictions and see if there is a corresponding actual morepork in the test data
#     # So if a morepork prediction was made, then there is a morepork in the test data, then we have a true positive.
#     # but if a morepork prediction was made, and there is NO corresponding morepork in the test data, then we have a false positive
#     first_test_data_recording_id = 537910
#     last_test_data_recording_id = 563200
#     
#   
#     cur = get_database_connection().cursor()
#     cur.execute("SELECT ID, recording_id, startTime, duration, predictedByModel from model_run_result WHERE predictedByModel = 'morepork_more-pork' AND modelRunName = ? AND recording_id > ? AND recording_id < ? ORDER BY recording_id ASC", (model_run_name, first_test_data_recording_id, last_test_data_recording_id))
# 
#     model_predictions = cur.fetchall()
#     number_of_predictions = len(model_predictions)
#     print("There are ", number_of_predictions, " predictions")
#     
#     total_of_true_positives = 0
#     total_of_false_positives = 0
#     
#     for model_prediction in model_predictions:
#         test_data_found_for_prediction = False
# #         print(model_prediction)
#         model_run_result_ID = model_prediction[0]
#         recording_id = model_prediction[1]
#         prediction_startTime = model_prediction[2]
#         duration = model_prediction[3]
#         prediction_endTime = prediction_startTime + duration
#         predictedByModel = model_prediction[4]
#         
#         print("recording_id ",recording_id, "predictedByModel ", predictedByModel, " prediction_startTime ", prediction_startTime, "prediction_endTime ", prediction_endTime)
#         
# #         cur.execute("SELECT recording_id, start_time_seconds, finish_time_seconds FROM test_data WHERE recording_id = ? AND (what = 'morepork_more-pork' OR what = 'maybe_morepork_more-pork') AND ((start_time_seconds > ? AND start_time_seconds < ?) OR (finish_time_seconds > ? AND finish_time_seconds < ?))", (recording_id, startTime, endTime,  startTime, endTime))
#         cur.execute("SELECT recording_id, start_time_seconds, finish_time_seconds, what FROM test_data WHERE recording_id = ? AND (what = 'morepork_more-pork' OR what = 'maybe_morepork_more-pork') ORDER BY start_time_seconds ASC", (recording_id,))
#         test_data_rows = cur.fetchall() 
#         for test_data_row in  test_data_rows: 
#                      
#             test_data_recording_id = test_data_row[0]            
#             test_data_start_time_seconds =  test_data_row[1]
#             test_data_finish_time_seconds = test_data_row[2]
#             test_data_what = test_data_row[3]
#             print("recording_id ",recording_id, " test_data_start_time_seconds ", test_data_start_time_seconds, "test_data_finish_time_seconds ", test_data_finish_time_seconds, "test_data_what ", test_data_what)  
#             
#             if do_rectangle_times_overlap(prediction_startTime, prediction_endTime, test_data_start_time_seconds, test_data_finish_time_seconds):
#                 print("Overlap ", test_data_what)
#                 test_data_found_for_prediction = True
#                 break
#                 
#         if test_data_found_for_prediction:
#             total_of_true_positives += 1  
#             sql = ''' UPDATE model_run_result
#                 SET true_positive = 1, actual_confirmed = ?               
#                 WHERE ID = ?'''        
#             cur.execute(sql, (test_data_what, model_run_result_ID))        
#             get_database_connection().commit() 
#             
#         else:
#             total_of_false_positives += 1
#             sql = ''' UPDATE model_run_result
#                 SET false_positive = 1             
#                 WHERE ID = ?'''        
#             cur.execute(sql, (model_run_result_ID,))        
#             get_database_connection().commit()
#             
#     print("total_of_true_positives is ", total_of_true_positives)
#     print("total_of_false_positives is ", total_of_false_positives)
    
def update_model_run_result_analysis():
    # This is going to look at all the model predictions (which indirectly means all onsets) and see if and what the corresponding test_data is
    # If model predicts a morepork, and test data has either a morepork, or maybe_morepork, then it is a True Positive
    # If a morepork prediction was made, and there is NO corresponding morepork in the test data, then we have a False Positive
    # If a non morepork prediction was made, and either there is no entry in the test_data, or the test_data has an entry which is NOT morepork, then it is a True Negative
    
    
    
    
    # So if a morepork prediction was made, then there is a morepork in the test data, then we have a true positive.
    # but if a morepork prediction was made, and there is NO corresponding morepork in the test data, then we have a false positive
    first_test_data_recording_id = 537910
    last_test_data_recording_id = 563200
    
  
    cur = get_database_connection().cursor()
#     cur.execute("SELECT ID, recording_id, startTime, duration, predictedByModel from model_run_result WHERE predictedByModel = 'morepork_more-pork' AND modelRunName = ? AND recording_id > ? AND recording_id < ? ORDER BY recording_id ASC", (model_run_name, first_test_data_recording_id, last_test_data_recording_id))
    cur.execute("SELECT ID, recording_id, startTime, duration, predictedByModel, probability from model_run_result WHERE modelRunName = ? AND recording_id > ? AND recording_id < ? ORDER BY recording_id ASC", (model_run_name, first_test_data_recording_id, last_test_data_recording_id))

    model_predictions = cur.fetchall()
    number_of_predictions = len(model_predictions)
    print("There are ", number_of_predictions, " predictions")
    
    total_of_true_positives = 0
    total_of_false_positives = 0
    total_of_true_negatives = 0
   
    count = 0
    for model_prediction in model_predictions:
        count+=1
        print(count, " of ", number_of_predictions)
        
        true_positive = 0 
        false_positive = 0
        true_negative = 0
#         false_negative = 0
        test_data_found_for_prediction = False
#         print(model_prediction)
        model_run_result_ID = model_prediction[0]
        recording_id = model_prediction[1]
        prediction_startTime = model_prediction[2]
        prediction_duration = model_prediction[3]
        prediction_endTime = prediction_startTime + prediction_duration
        predictedByModel = model_prediction[4]
        probability = model_prediction[5]
        
        #print("recording_id ",recording_id, "predictedByModel ", predictedByModel, " prediction_startTime ", prediction_startTime, "prediction_endTime ", prediction_endTime)
        
#         cur.execute("SELECT recording_id, start_time_seconds, finish_time_seconds FROM test_data WHERE recording_id = ? AND (what = 'morepork_more-pork' OR what = 'maybe_morepork_more-pork') AND ((start_time_seconds > ? AND start_time_seconds < ?) OR (finish_time_seconds > ? AND finish_time_seconds < ?))", (recording_id, startTime, endTime,  startTime, endTime))
        cur.execute("SELECT ID, recording_id, start_time_seconds, finish_time_seconds, what FROM test_data WHERE recording_id = ? AND (what = 'morepork_more-pork' OR what = 'maybe_morepork_more-pork') ORDER BY start_time_seconds ASC", (recording_id,))
        test_data_rows = cur.fetchall() 
        
        for test_data_row in  test_data_rows: 
            test_data_ID = test_data_row[0]         
            test_data_recording_id = test_data_row[1]            
            test_data_start_time_seconds =  test_data_row[2]
            test_data_finish_time_seconds = test_data_row[3]
            test_data_what = test_data_row[4]
#             print("recording_id ",recording_id, " test_data_start_time_seconds ", test_data_start_time_seconds, "test_data_finish_time_seconds ", test_data_finish_time_seconds, "test_data_what ", test_data_what)  
            
            if do_rectangle_times_overlap(prediction_startTime, prediction_endTime, test_data_start_time_seconds, test_data_finish_time_seconds):
                print("Overlap ", test_data_what)
                test_data_found_for_prediction = True
                break
            
        if test_data_found_for_prediction:
            # As there is test data for this prediction, we need to check what the prediction is against the test data
            if predictedByModel == 'morepork_more-pork':                
                if (test_data_what == 'morepork_more-pork' or test_data_what == 'maybe_morepork_more-pork'):
                    # Predicted morepork, and test_data says it really is
                    total_of_true_positives +=1
                    true_positive = 1 
                    false_positive = 0
                    true_negative = 0
                    print("Count of true positives ", total_of_true_positives)
                else:
                    # Predicted morepork, and test_data says it isn't
                    total_of_false_positives +=1
                    true_positive = 0 
                    false_positive = 1
                    true_negative = 0
                    print("Count of false positives ", total_of_false_positives)
                    
                    
            else:
                # The prediction was NOT morepork, so need to check if the test data that was found agrees
                # If test_data says it was a morepork then this is a false negative
                # but if the test data said it wasn't a morepork, then this is a True Negative
                if test_data_what == 'morepork_more-pork':
                    true_positive = 0 
                    false_positive = 0
                    true_negative = 0
                    print("A false negative, but not counting these as it won't find them all - Need to query the test_data table and find test_data with no and incorrect predictions")
                else:
                    # The prediction was NOT a morepork, and the test_data at this location was also NOT a morepork, so a True Negative
                    total_of_true_negatives +=1
                    true_positive = 0 
                    false_positive = 0
                    true_negative = 1
                    print("Count of true negatives ", total_of_true_negatives)
                    
            cur = get_database_connection().cursor()
                           
            sql = ''' REPLACE INTO model_run_result_analysis (modelRunName, recording_id, prediction_startTime, prediction_duration, predictedByModel, probability, test_data_ID, test_data_what, test_data_start_time_seconds, test_data_finish_time_seconds, true_positive, false_positive, true_negative)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) '''   
            cur.execute(sql, (model_run_name, recording_id, prediction_startTime, prediction_duration, predictedByModel, probability, test_data_ID, test_data_what, test_data_finish_time_seconds, test_data_finish_time_seconds, true_positive, false_positive, true_negative))  
            get_database_connection().commit() 
                    
        else:
            # No test data was found for this prediction
            # If prediction was morepork, then it is a false positive
            # but if the prediction was not morepork, then it is a true negative
            if predictedByModel == 'morepork_more-pork':
                # If prediction was morepork, then it is a false positive
                total_of_false_positives +=1
                true_positive = 0 
                false_positive = 1
                true_negative = 0
            else:
                # but if the prediction was not morepork, then it is a true negative
                total_of_true_negatives +=1
                true_positive = 0 
                false_positive = 0
                true_negative = 1
                
                            
           
            cur = get_database_connection().cursor()
                    
            sql = ''' REPLACE INTO model_run_result_analysis (modelRunName, recording_id, prediction_startTime, prediction_duration, predictedByModel, probability,true_positive, false_positive, true_negative)
              VALUES(?,?,?,?,?,?,?,?,?) '''
            cur.execute(sql, (model_run_name, recording_id, prediction_startTime, prediction_duration, predictedByModel, probability, true_positive, false_positive, true_negative)) 
            get_database_connection().commit()
        
         
        

    print("total_of_true_positives is ", total_of_true_positives)
    print("total_of_false_positives is ", total_of_false_positives)
    print("total_of_true_negatives is ", total_of_true_negatives)
    
def update_test_data_analyis():
    # This is going to look at all the (morepork) test_data and see if the model made a prediction for each of them (and what prediction)
    # So if the test data has an actual morepork, and the model predicts a morepork, we have a true positive
    # But if the test data has an actual morepork and the model does NOT have a morepork, then we have false negative
     
#     first_test_data_recording_id = 537910
#     last_test_data_recording_id = 563200
    total_of_true_positives = 0
    total_of_false_negatives = 0
    
    
    cur = get_database_connection().cursor()
    cur.execute("SELECT ID, recording_id, start_time_seconds, finish_time_seconds, what FROM test_data WHERE what = 'morepork_more-pork' ORDER BY recording_id, start_time_seconds ASC")
    test_data_rows = cur.fetchall() 
    number_of_test_data_rows = len(test_data_rows)
    count = 0    
    for test_data_row in  test_data_rows:
        count+=1
        prediction_found_for_test_data = False
        test_data_ID = test_data_row[0]           
        test_data_recording_id = test_data_row[1]            
        test_data_start_time_seconds =  test_data_row[2]
        test_data_finish_time_seconds = test_data_row[3]
        test_data_what = test_data_row[4]
        print(count, " of ",number_of_test_data_rows, ": recording_id ",test_data_recording_id, " test_data_start_time_seconds ", test_data_start_time_seconds, "test_data_finish_time_seconds ", test_data_finish_time_seconds, "test_data_what ", test_data_what)  
                 
        # For each of the test data, look to see there is a prediction
        cur.execute("SELECT ID, recording_id, startTime, duration, predictedByModel, probability from model_run_result WHERE predictedByModel = 'morepork_more-pork' AND modelRunName = ? AND recording_id = ? ORDER BY recording_id ASC", (model_run_name, test_data_recording_id))
        model_predictions = cur.fetchall()
        number_of_predictions = len(model_predictions)
        for model_prediction in model_predictions:
            model_run_result_ID = model_prediction[0]
            recording_id = model_prediction[1]
            prediction_startTime = model_prediction[2]
            duration = model_prediction[3]
            prediction_endTime = prediction_startTime + duration
            predictedByModel = model_prediction[4]
            probability = model_prediction[5]
            
            print("recording_id ",recording_id, "predictedByModel ", predictedByModel, " prediction_startTime ", prediction_startTime, "prediction_endTime ", prediction_endTime)
            
            # Now determine if a prediction overlaps with a test_data
            if do_rectangle_times_overlap(prediction_startTime, prediction_endTime, test_data_start_time_seconds, test_data_finish_time_seconds):
                print("Overlap ", test_data_what)
                prediction_found_for_test_data = True
                break
            
        if prediction_found_for_test_data:
            total_of_true_positives += 1  
            true_positive = 1
            false_negative = 0
        else:
            total_of_false_negatives += 1  
            true_positive = 0
            false_negative = 1
            
                      
        # Now store or updata database with this information 
        # https://www.sqlitetutorial.net/sqlite-replace-statement/    
        # Relies on a unique index in the table on columns modelRunResultRunName and test_data_id       
        
        sql = ''' REPLACE INTO test_data_analysis(modelRunResultRunName, recording_id, test_data_id, test_data_start_time_seconds, test_data_finish_time, test_data_what, predictedByModel, probability, true_positive, false_negative)
              VALUES(?,?,?,?,?,?,?,?,?,?) '''
        cur = get_database_connection().cursor()
        cur.execute(sql, (model_run_name, recording_id, test_data_ID, test_data_start_time_seconds, test_data_finish_time_seconds, test_data_what, predictedByModel, probability, true_positive, false_negative))           
        get_database_connection().commit() 
        
       
        
    print("total_of_true_positives is ", total_of_true_positives)
    print("total_of_false_negatives is ", total_of_false_negatives)
        
def test111():
    a = True
    b = True
    
    if a == True and b == True:
        if a == True or b == True:
            print("yipee")
            
def update_model_run_result_actual_confirmed_from_test_data():
    # Use this to update each row in the model_run_table with the actual sound (if there exists one) from the test data
#     model_run_name = '2020_06_05_1'
    modelRunName = "2020_06_12_2" # This is the first tensorflow model that I've tested
    cur = get_database_connection().cursor()
    cur.execute("SELECT ID, recording_id, startTime, duration, predictedByModel from model_run_result WHERE modelRunName = ? ORDER BY recording_id ASC", (modelRunName,))

    model_run_results = cur.fetchall()
    number_of_model_run_results = len(model_run_results)
    print("There are ", number_of_model_run_results, " predictions")
    
    count = 0
    count_of_predictions_with_overlapping_test_data = 0
    count_of_morepork_predictions_with_overlapping_morepork_test_data = 0
    count_of_true_positives = 0
    count_of_false_positives = 0
    for model_run_result in model_run_results:
        count+=1
        print(count, " of ", number_of_model_run_results)
        
        
        model_run_result_ID = model_run_result[0]
        recording_id = model_run_result[1]
        prediction_startTime = model_run_result[2]
        prediction_duration = model_run_result[3]
        prediction_endTime = prediction_startTime + prediction_duration
        predictedByModel = model_run_result[4]
        
    
        # Find if there is a test_data value for this onset/prediction
        cur.execute("SELECT ID, what, start_time_seconds, finish_time_seconds from test_data WHERE recording_id = ?", (recording_id,))
        test_data_rows = cur.fetchall()
        test_data_found = False
        actual_confirmed = "no_test_data"
        for test_data_row in test_data_rows:
            results_id = test_data_row[0]
            actual_confirmed = test_data_row[1]
            test_data_start_time_seconds = test_data_row[2]
            test_data_finish_time_seconds = test_data_row[3]
            
            if do_rectangle_times_overlap(prediction_startTime, prediction_endTime, test_data_start_time_seconds, test_data_finish_time_seconds):                      
                print("Predicted: ",predictedByModel, " actual_confirmed: ", actual_confirmed )
                test_data_found = True
                break
            
        if test_data_found:
            count_of_predictions_with_overlapping_test_data+=1
            if predictedByModel == "morepork_more-pork" and actual_confirmed == "morepork_more-pork":
                print("True Positive") 
                count_of_true_positives+=1
            else:
                count_of_false_positives+=1
        else:
            # Still need to check if this is a false positive
            if predictedByModel == "morepork_more-pork":
                # Predicted morepork, but no morepork test data exists
                count_of_false_positives+=1
#                 actual_confirmed = "no_test_data"
        
#         table = "model_run_result"        
        sql = "UPDATE model_run_result SET actual_confirmed = ? WHERE ID = ?"
            
        cur.execute(sql, (actual_confirmed, model_run_result_ID))        
        get_database_connection().commit() 
            
    print("count_of_predictions_with_overlapping_test_data ", count_of_predictions_with_overlapping_test_data)
    
    print("count_of_true_positives ", count_of_true_positives)
    print("count_of_false_positives ", count_of_false_positives)
   
            
def test_data_analysis_using_version_7_onsets_with_spectrogram_based_prediction():
#     modelRunName = "2020_06_05_1"
    modelRunName = "2020_06_12_2" # This is the first tensorflow model that I've tested
    
    cur = get_database_connection().cursor()
    cur.execute("SELECT ID, recording_id, start_time_seconds, finish_time_seconds, what FROM test_data WHERE what = 'morepork_more-pork' ORDER BY recording_id, start_time_seconds ASC")
    test_data_rows = cur.fetchall() 
    count_of_test_data_rows = len(test_data_rows)
    print("count_of_test_data_rows ", count_of_test_data_rows)
    count = 0
    for test_data_row in test_data_rows:
        count+=1
        print(count, " of ", count_of_test_data_rows)
        test_data_id = test_data_row[0]
        recording_id = test_data_row[1]
        test_data_start_time_seconds = test_data_row[2]
        test_data_finish_time_seconds = test_data_row[3]
        test_data_what = test_data_row[4]        
        
        cur.execute("SELECT ID, recording_id, startTime, duration, predictedByModel, probability from model_run_result WHERE modelRunName = ? AND recording_id = ?", (modelRunName, recording_id))
        model_run_result_rows = cur.fetchall() 
        model_run_result_predictedByModel = ""
        
        for model_run_result_row in model_run_result_rows:
            model_run_result_id = model_run_result_row[0]
            
            model_run_result_startTime = model_run_result_row[2]
            model_run_result_duration = model_run_result_row[3]            
            model_run_result_finish_time = model_run_result_startTime + model_run_result_duration
            model_run_result_predictedByModel = model_run_result_row[4]  
            model_run_result_probability =   model_run_result_row[5]  
            
            if do_rectangle_times_overlap(model_run_result_startTime, model_run_result_finish_time, test_data_start_time_seconds, test_data_finish_time_seconds):                      
                print("model_run_result_predictedByModel: ",model_run_result_predictedByModel, " test_data_what: ", test_data_what )
                model_run_result_found = True
                break
        
        if model_run_result_found:
            print("model_run_result_predictedByModel ", model_run_result_predictedByModel)
        else:
            print("No prediction found")
            model_run_result_predictedByModel = "no_prediction_found"
            
            
        
        cur = get_database_connection().cursor()
                    
        sql = ''' REPLACE INTO model_run_result_analysis (modelRunName, recording_id, prediction_startTime, prediction_duration, predictedByModel, probability)
          VALUES(?,?,?,?,?,?) '''
        cur.execute(sql, (modelRunName, recording_id, model_run_result_startTime, model_run_result_duration, model_run_result_predictedByModel, model_run_result_probability )) 
        get_database_connection().commit()

def tensorflow_hello_world():
    model = tf.keras.Sequential([tf.keras.layers.Dense(units=1, input_shape=[1])])
    model.compile(optimizer='sgd', loss='mean_squared_error')
    
    xs = np.array([-1.0, 0.0, 1.0, 2.0, 3.0, 4.0], dtype=float)
    ys = np.array([-3.0, -1.0, 1.0, 3.0, 5.0, 7.0], dtype=float)
    
    model.fit(xs, ys, epochs=50)
    
    print(model.predict([10.0]))      

def create_single_focused_mel_spectrogram(recording_id, start_time_seconds, duration_seconds, actual_confirmed):
    spectrogram_folder_path = tensorflow_spectrogram_images + '/' + actual_confirmed
    print(spectrogram_folder_path)
    if not os.path.exists(spectrogram_folder_path):
        os.makedirs(spectrogram_folder_path) 

      

    try:
        
        audio_filename = str(recording_id) + '.m4a'
        audio_in_path = base_folder + '/' + downloaded_recordings_folder + '/' +  audio_filename 
        image_out_name = str(recording_id) + '$' + str(start_time_seconds) + '$' + actual_confirmed +'.jpg'
        print('image_out_name', image_out_name)           
       
        image_out_path = spectrogram_folder_path + '/' + image_out_name
        
        y, sr = librosa.load(audio_in_path, sr=None)      
               
        start_time_seconds_float = float(start_time_seconds)            
        
        start_position_array = int(sr * start_time_seconds_float)              
                   
        end_position_array = start_position_array + int((sr * duration_seconds))                  
                    
        y_part = y[start_position_array:end_position_array]  
        mel_spectrogram = librosa.feature.melspectrogram(y=y_part, sr=sr, n_mels=32, fmin=700,fmax=1000)
        
        plt.axis('off') # no axis
        plt.axes([0., 0., 1., 1.], frameon=False, xticks=[], yticks=[]) # Remove the white edge
        librosa.display.specshow(mel_spectrogram, cmap='binary') #https://matplotlib.org/examples/color/colormaps_reference.html
        plt.savefig(image_out_path, bbox_inches=None, pad_inches=0)
        plt.close()
        
#         return get_image(image_out_path)
        
    except Exception as e:
        print(e, '\n')
        print('Error processing onset ', onset)

def create_spectrogram_images_for_tensorflow():
    

    cur = get_database_connection().cursor()
    cur.execute("SELECT ID, recording_id, start_time_seconds, duration_seconds, actual_confirmed from onsets WHERE version = 5 AND actual_confirmed IS NOT NULL AND (recording_id < ? OR recording_id > ?)", (first_test_data_recording_id, last_test_data_recording_id))
    confirmed_onsets = cur.fetchall() 
    count_of_confirmed_onsets = len(confirmed_onsets)
    print("count_of_confirmed_onsets ", count_of_confirmed_onsets)
    count = 0
    for confired_onset in confirmed_onsets:
        count+=1
        print(count, ' of ', count_of_confirmed_onsets)
        recording_id = confired_onset[1]
        start_time_seconds = confired_onset[2]
        duration_seconds = confired_onset[3]
        actual_confirmed = confired_onset[4]    
        
        create_single_focused_mel_spectrogram(recording_id, start_time_seconds, duration_seconds, actual_confirmed)
        
def create_temp_single_focused_mel_spectrogram_for_tensorflow(recording_id, start_time_seconds, duration_seconds, image_out_path_name):
    
#     spectrogram_folder_path = base_folder + '/Audio_Analysis/temp'
#     print(spectrogram_folder_path)
#     if not os.path.exists(spectrogram_folder_path):
#         os.makedirs(spectrogram_folder_path)      

    try:
        
        audio_filename = str(recording_id) + '.m4a'
        audio_in_path = base_folder + '/' + downloaded_recordings_folder + '/' +  audio_filename 
               
       
#         image_out_path = spectrogram_folder_path + '/' + image_out_name
        
        y, sr = librosa.load(audio_in_path, sr=None)      
               
        start_time_seconds_float = float(start_time_seconds)            
        
        start_position_array = int(sr * start_time_seconds_float)              
                   
        end_position_array = start_position_array + int((sr * duration_seconds))                  
                    
        y_part = y[start_position_array:end_position_array]  
        mel_spectrogram = librosa.feature.melspectrogram(y=y_part, sr=sr, n_mels=32, fmin=700,fmax=1000)
        
        plt.axis('off') # no axis
        plt.axes([0., 0., 1., 1.], frameon=False, xticks=[], yticks=[]) # Remove the white edge
        librosa.display.specshow(mel_spectrogram, cmap='binary') #https://matplotlib.org/examples/color/colormaps_reference.html
        plt.savefig(image_out_path_name, bbox_inches=None, pad_inches=0)
        plt.close()
        
#         return get_image(image_out_path)
        
    except Exception as e:
        print(e, '\n')
        print('Error processing onset ', onset)

def classify_march_test_data_using_tensorflow_model():
    tensorflow_run_name = '2020_06_12_2'
    tensorflow_run_folder = base_folder + '/Audio_Analysis/audio_classifier_runs/tensorflow_runs' + '/' + tensorflow_run_name
    path_to_model = tensorflow_run_folder + "/model"
    cut_off = 0.5
    
    reconstructed_model = tf.keras.models.load_model(path_to_model)    
    
    
    spectrogram_folder_path = base_folder + '/Audio_Analysis/temp'
    print(spectrogram_folder_path)
    if not os.path.exists(spectrogram_folder_path):
        os.makedirs(spectrogram_folder_path) 
        
    image_out_path_name = spectrogram_folder_path + "/" + 'temp.jpg'     

    cur = get_database_connection().cursor()
#     cur.execute("SELECT ID, recording_id, start_time_seconds, duration_seconds, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ  from onsets WHERE version = 7 AND (recording_id > ? AND recording_id < ?)", (first_test_data_recording_id, last_test_data_recording_id))
    cur.execute("SELECT ID, recording_id, start_time_seconds, duration_seconds, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ  from onsets WHERE version = 7 AND recordingDateTimeNZ BETWEEN ? AND ? ORDER BY recordingDateTimeNZ", ("2020-03-01 00:00", "2020-03-31 23:59"))
    confirmed_onsets = cur.fetchall() 
    count_of_confirmed_onsets = len(confirmed_onsets)
    print("count_of_confirmed_onsets ", count_of_confirmed_onsets)
    count = 0
    
    for confired_onset in confirmed_onsets:
        count+=1
        print(count, ' of ', count_of_confirmed_onsets)
        recording_id = confired_onset[1]
        start_time_seconds = confired_onset[2]
        duration_seconds = confired_onset[3]
        device_super_name = confired_onset[4]
        device_name = confired_onset[5]
        recordingDateTime = confired_onset[6]
        recordingDateTimeNZ = confired_onset[7]
               
       
#         create_single_focused_mel_spectrogram(recording_id, start_time_seconds, duration_seconds, image_out_path_name )
        create_temp_single_focused_mel_spectrogram_for_tensorflow(recording_id, start_time_seconds, duration_seconds, image_out_path_name)
        
        # Now test spectrogram image against model
        img = tf.keras.preprocessing.image.load_img(image_out_path_name, target_size=[320, 240], color_mode="grayscale")
        x = tf.keras.preprocessing.image.img_to_array(img)        
        x = tf.keras.applications.mobilenet.preprocess_input(x[tf.newaxis,...])
        result = reconstructed_model(x)
        what = ""
        probability = result.numpy()[0][0] # https://stackoverflow.com/questions/49568041/tensorflow-how-do-i-convert-a-eagertensor-into-a-numpy-array
        print("probability ", probability)
#         if result[0] < cut_off:
        if probability < cut_off:
            print("morepork")
            what = "morepork_more-pork"
           
        else:
            print("other")
            what = "other"
            
        probability_str = str(probability)
           
        sql = ''' INSERT INTO model_run_result(modelRunName, recording_id, startTime, duration, predictedByModel, probability, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ)
                  VALUES(?,?,?,?,?,?,?,?,?,?) '''
        cur.execute(sql, (tensorflow_run_name, recording_id, start_time_seconds, duration_seconds, what, probability_str, device_super_name, device_name, recordingDateTime, recordingDateTimeNZ))
        get_database_connection().commit()
                        
        
def split_data(SOURCE, TRAINING, TESTING, SPLIT_SIZE):
    files = []
    for filename in os.listdir(SOURCE):
        file = SOURCE + filename
        if os.path.getsize(file) > 0:
            files.append(filename)
        else:
            print(filename + " is zero length, so ignoring.")

    training_length = int(len(files) * SPLIT_SIZE)
    testing_length = int(len(files) - training_length)
    shuffled_set = random.sample(files, len(files))
    training_set = shuffled_set[0:training_length]
    testing_set = shuffled_set[-testing_length:]

    for filename in training_set:
        this_file = SOURCE + filename
        destination = TRAINING + filename
        copyfile(this_file, destination)
        
#     print(TRAINING, ' has ', str(len(TRAINING)) + ' files.')

    for filename in testing_set:
        this_file = SOURCE + filename
        destination = TESTING + filename
        copyfile(this_file, destination)        
    
#     print(TESTING, ' has ', str(len(TESTING)) + ' files.\n')

def call_split_data():    
    
    split_size = .9
    all_image_input_directories = os.listdir(tensorflow_spectrogram_images)
    for input_directory in all_image_input_directories:
        
#         training_input_directory_path = tensorflow_run_folder + '/training/' + input_directory + '/' 
        training_input_directory_path = tensorflow_spectrogram_images + '/training/' + input_directory + '/'             
        if not os.path.exists(training_input_directory_path):
            os.makedirs(training_input_directory_path) 
            
#         testing_input_directory_path = tensorflow_run_folder + '/validation/' + input_directory + '/'
        testing_input_directory_path = tensorflow_spectrogram_images + '/validation/' + input_directory + '/'                      
        if not os.path.exists(testing_input_directory_path):
            os.makedirs(testing_input_directory_path) 
            
        source_dir = tensorflow_spectrogram_images + '/' + input_directory + '/'
        
        split_data(source_dir, training_input_directory_path, testing_input_directory_path, split_size)
        
#         list = os.listdir(training_input_directory_path) # dir is your directory path
#         number_files = len(list)
        print(training_input_directory_path, ' has ', len(os.listdir(training_input_directory_path)), 'files')
        print(testing_input_directory_path, ' has ', len(os.listdir(testing_input_directory_path)), 'files')
        
         

def build_model1():  # used for      tensorflow_run_name = '2020_06_08_1'
    
    learning_rate = 1e-4
    # https://www.tensorflow.org/api_docs/python/tf/keras/activations
    model = tf.keras.models.Sequential([

    # https://machinelearningmastery.com/rectified-linear-activation-function-for-deep-learning-neural-networks/
    tf.keras.layers.Conv2D(16, (3, 3), activation='relu', input_shape=(320, 240, 3)),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(32, (3, 3), activation='relu'),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(512, activation='relu'),
    tf.keras.layers.Dense(25, activation='softmax')
    ])

#     model.compile(optimizer=Adam(learning_rate),loss='sparse_categorical_crossentropy',  metrics=['accuracy'])
#     model.compile(loss='categorical_crossentropy', optimizer='rmsprop',  metrics=['accuracy'])
    model.compile(optimizer=Adam(learning_rate), loss='categorical_crossentropy',  metrics=['accuracy'])
    
    return model

def build_model2():  # used for      tensorflow_run_name = '2020_06_08_1'
    
#     learning_rate = 1e-4
    learning_rate = 1e-4
    # https://www.tensorflow.org/api_docs/python/tf/keras/activations
    model = tf.keras.models.Sequential([

    # https://machinelearningmastery.com/rectified-linear-activation-function-for-deep-learning-neural-networks/
    tf.keras.layers.Conv2D(16, (3, 3), activation='relu', input_shape=(320, 240, 3)),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(32, (3, 3), activation='relu'),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(512, activation='relu'),
#     tf.keras.layers.Dense(25, activation='softmax')
    tf.keras.layers.Dense(1, activation='sigmoid')
    ])

#     model.compile(optimizer=Adam(learning_rate),loss='sparse_categorical_crossentropy',  metrics=['accuracy'])
#     model.compile(loss='categorical_crossentropy', optimizer='rmsprop',  metrics=['accuracy'])
#     model.compile(optimizer=Adam(learning_rate), loss='categorical_crossentropy',  metrics=['accuracy'])
    model.compile(optimizer=RMSprop(lr=learning_rate), loss='binary_crossentropy',  metrics=['accuracy'])
    
    return model

def build_model3():  # used for      tensorflow_run_name = '2020_06_08_1'
    
#     learning_rate = 1e-4
    learning_rate = 1e-4
    # https://www.tensorflow.org/api_docs/python/tf/keras/activations
    model = tf.keras.models.Sequential([

    # https://machinelearningmastery.com/rectified-linear-activation-function-for-deep-learning-neural-networks/
    tf.keras.layers.Conv2D(16, (3, 3), kernel_regularizer=regularizers.l2(0.0001), activation='relu', input_shape=(320, 240, 3)),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(32, (3, 3), kernel_regularizer=regularizers.l2(0.0001), activation='relu'),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(64, (3, 3), kernel_regularizer=regularizers.l2(0.0001),  activation='relu'),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(512, activation='relu'),
#     tf.keras.layers.Dense(25, activation='softmax')
    tf.keras.layers.Dense(1, activation='sigmoid')
    ])

#     model.compile(optimizer=Adam(learning_rate),loss='sparse_categorical_crossentropy',  metrics=['accuracy'])
#     model.compile(loss='categorical_crossentropy', optimizer='rmsprop',  metrics=['accuracy'])
#     model.compile(optimizer=Adam(learning_rate), loss='categorical_crossentropy',  metrics=['accuracy'])
    model.compile(optimizer=RMSprop(lr=learning_rate), loss='binary_crossentropy',  metrics=['accuracy'])
    
    return model



def build_model4():  # used for      tensorflow_run_name = '2020_06_08_1'
    
#     learning_rate = 1e-4
    learning_rate = 1e-4
    # https://www.tensorflow.org/api_docs/python/tf/keras/activations
    model = tf.keras.models.Sequential([

    # https://machinelearningmastery.com/rectified-linear-activation-function-for-deep-learning-neural-networks/
    tf.keras.layers.Conv2D(16, (3, 3), kernel_regularizer=regularizers.l2(0.0001), activation='relu', input_shape=(320, 240, 3)),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(32, (3, 3), kernel_regularizer=regularizers.l2(0.0001), activation='relu'),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(64, (3, 3), kernel_regularizer=regularizers.l2(0.0001),  activation='relu'),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(512, activation='relu'),
#     tf.keras.layers.Dense(25, activation='softmax')
    tf.keras.layers.Dense(1, activation='sigmoid')
    ])

#     model.compile(optimizer=Adam(learning_rate),loss='sparse_categorical_crossentropy',  metrics=['accuracy'])
#     model.compile(loss='categorical_crossentropy', optimizer='rmsprop',  metrics=['accuracy'])
#     model.compile(optimizer=Adam(learning_rate), loss='categorical_crossentropy',  metrics=['accuracy'])
    
    # https://www.tensorflow.org/tutorials/keras/overfit_and_underfit
    


    
#     model.compile(optimizer=RMSprop(lr=learning_rate), loss='binary_crossentropy',  metrics=['accuracy'])
    model.compile(optimizer=get_optimizer(), loss='binary_crossentropy',  metrics=['accuracy'])
    
    return model

# def get_optimizer():
# #   return tf.keras.optimizers.Adam(lr_schedule)
#     return tf.keras.optimizers.RMSprop(lr_schedule)

def build_model5():  # used for      tensorflow_run_name = '2020_06_08_1'
    
#     learning_rate = 1e-4
    learning_rate = 1e-4
    # https://www.tensorflow.org/api_docs/python/tf/keras/activations
    model = tf.keras.models.Sequential([

    # https://machinelearningmastery.com/rectified-linear-activation-function-for-deep-learning-neural-networks/
    tf.keras.layers.Conv2D(16, (3, 3), kernel_regularizer=regularizers.l2(0.0001), activation='relu', input_shape=(320, 240, 3)),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(32, (3, 3), kernel_regularizer=regularizers.l2(0.0001), activation='relu'),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(32, (3, 3), kernel_regularizer=regularizers.l2(0.0001),  activation='relu'),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Dropout(0.5),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(256, activation='relu'),
#     tf.keras.layers.Dense(25, activation='softmax')
    tf.keras.layers.Dense(1, activation='sigmoid')
    ])

#     model.compile(optimizer=Adam(learning_rate),loss='sparse_categorical_crossentropy',  metrics=['accuracy'])
#     model.compile(loss='categorical_crossentropy', optimizer='rmsprop',  metrics=['accuracy'])
#     model.compile(optimizer=Adam(learning_rate), loss='categorical_crossentropy',  metrics=['accuracy'])
    
    # https://www.tensorflow.org/tutorials/keras/overfit_and_underfit
    


    
#     model.compile(optimizer=RMSprop(lr=learning_rate), loss='binary_crossentropy',  metrics=['accuracy'])
    model.compile(optimizer=get_optimizer(), loss='binary_crossentropy',  metrics=['accuracy'])
    
    return model

STEPS_PER_EPOCH = 40

lr_schedule = tf.keras.optimizers.schedules.InverseTimeDecay(
      0.001,
      decay_steps=STEPS_PER_EPOCH*1000,
      decay_rate=1,
      staircase=False)


def get_optimizer():
    return tf.keras.optimizers.RMSprop(lr_schedule)

 # https://www.tensorflow.org/api_docs/python/tf/keras/activations
 # https://machinelearningmastery.com/rectified-linear-activation-function-for-deep-learning-neural-networks/
 
def build_model6():      
   
    model = tf.keras.models.Sequential([
    
    tf.keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(320, 240, 1)),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(16, (3, 3), activation='relu'),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Conv2D(16, (3, 3), activation='relu'),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.MaxPooling2D(2, 2),
    tf.keras.layers.Dropout(0.3),
    tf.keras.layers.Flatten(),
    tf.keras.layers.Dense(64, activation='relu'),
#     tf.keras.layers.Dense(1, activation='sigmoid')
#     tf.keras.layers.Dense(1, activation='softmax')
    tf.keras.layers.Dense(1, activation='swish')
    ])

    model.compile(optimizer=get_optimizer(), loss='binary_crossentropy',  metrics=['accuracy'])
    
    return model

def run_tensorflow():
    tensorflow_run_name = '2020_06_18_5'
    tensorflow_run_folder = base_folder + '/Audio_Analysis/audio_classifier_runs/tensorflow_runs' + '/' + tensorflow_run_name
    if not os.path.exists(tensorflow_run_folder):
        os.makedirs(tensorflow_run_folder)
        
    checkpoint_path = tensorflow_run_folder + "/training_1/cp.ckpt"
    
    class earlyStopCallback(tf.keras.callbacks.Callback):
        def on_epoch_end(self, epoch, logs={}):
            if(logs.get('accuracy')>0.999):
                print("\nAccuracy limit reached so cancelling training!")
                self.model.stop_training = True
                
    cp_callback = tf.keras.callbacks.ModelCheckpoint(checkpoint_path,
                                                     save_weights_only=True,
                                                     verbose=1)
    
    log_dir = tensorflow_run_folder +"/logs/fit/"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    tensorboard_callback = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)
        
    print('tensorflow version is ',tf.__version__)
    print('python version is ',sys.version)
    
#     training_input_directory_path = tensorflow_run_folder + '/training/'
#     testing_input_directory_path = tensorflow_run_folder + '/testing/'
    training_input_directory_path = tensorflow_spectrogram_images + '/training/'
    testing_input_directory_path = tensorflow_spectrogram_images + '/validation/'
    
    
    model = build_model6()
    model.summary()

    #     https://www.youtube.com/watch?v=0kYIZE8Gl90
    
    train_datagen = ImageDataGenerator(
        rescale=1./255,
#         width_shift_range=0.2,
#         height_shift_range=0.2,
#         zoom_range=0.2,
        fill_mode='nearest') 
    
    train_generator = train_datagen.flow_from_directory(
            training_input_directory_path,
            color_mode="grayscale",
#             target_size=(640, 480),
           
            target_size=(320, 240),
            batch_size=128,
#             class_mode='categorical')
            class_mode='binary') # Because I've changed images to be just morepork or other (I removed the maybe and part morepork)

    validation_datagen = ImageDataGenerator(rescale=1./255)
      
    validation_generator = validation_datagen.flow_from_directory(
            testing_input_directory_path,
             color_mode="grayscale",
            target_size=(320, 240),
            
#             target_size=(640, 480),
            batch_size=16,
#             class_mode='categorical')
            class_mode='binary')
    


    es_callback = earlyStopCallback()
    
    # steps_per_epoch = number_of_images / batch_ size = 5136 / 128 = 40.125 = 40
    # validation_steps = number_of_images / batch_ size = 584 / 16 = 36.5 = 36
    
    # steps_per_epoch = number_of_images / batch_ size = 5059 / 128 = 39.52 = 40
    # validation_steps = number_of_images / batch_ size = 564 / 16 = 35.25 = 35
    
    history = model.fit(
        train_generator, 
        epochs=1000, 
        validation_data = validation_generator, 
#         steps_per_epoch=40,
        steps_per_epoch=STEPS_PER_EPOCH,
        validation_steps=35,
        verbose = 2,
        callbacks=[es_callback, cp_callback, tensorboard_callback])
    
    #https://keras.io/guides/serialization_and_saving/
    path_to_model = tensorflow_run_folder + "/model"
    model.save(path_to_model)
    
  

def use_tensflow_model_test():
#     tensorflow_run_name = '2020_06_12_3'
#     tensorflow_run_name = '2020_06_12_2' # This looks best so far - 1.7% of other are incorrectly classified as morepork
#     tensorflow_run_name = '2020_06_12_1'
#     tensorflow_run_name = '2020_06_11_2'
    tensorflow_run_name = '2020_06_11_2'
    
    tensorflow_run_folder = base_folder + '/Audio_Analysis/audio_classifier_runs/tensorflow_runs' + '/' + tensorflow_run_name
    path_to_model = tensorflow_run_folder + "/model"
    
    cut_off = 0.5
    
    print(path_to_model)
    reconstructed_model = tf.keras.models.load_model(path_to_model)
    input_folder = tensorflow_spectrogram_images + "/validation/morepork_more-pork"
    count_of_TP = 0
    count_of_FP = 0
    for file in os.listdir(input_folder):
        img_path=input_folder + "/" + file
        print(file)
#         print(img_path)
#         img = tf.keras.preprocessing.image.load_img(img_path, target_size=[320, 240], color_mode="grayscale")
        img = tf.keras.preprocessing.image.load_img(img_path, target_size=[320, 240], color_mode="rgb")
        
        x = tf.keras.preprocessing.image.img_to_array(img)
        
        x = tf.keras.applications.mobilenet.preprocess_input(x[tf.newaxis,...])
        # print(x.shape)
        # print(x)
        
        
        result = reconstructed_model(x)
        if result[0] < cut_off:
            print(file + " is an morepork")
            count_of_TP +=1
        else:
            print(file + " is a other")
            count_of_FP +=1
            
        
#     input_folder = tensorflow_spectrogram_images + "/validation/other"
    input_folder = tensorflow_spectrogram_images + "/validation/other"
    count_of_TN = 0
    count_of_FN = 0
    for file in os.listdir(input_folder):
        img_path=input_folder + "/" + file
#         print(file)
#         print(img_path)
#         img = tf.keras.preprocessing.image.load_img(img_path, target_size=[320, 240], color_mode="grayscale")
        img = tf.keras.preprocessing.image.load_img(img_path, target_size=[320, 240], color_mode="rgb")
        
        x = tf.keras.preprocessing.image.img_to_array(img)
        
        x = tf.keras.applications.mobilenet.preprocess_input(x[tf.newaxis,...])
        # print(x.shape)
        # print(x)
        
        
        result = reconstructed_model(x)
        print(result)
        print(result[0])
        if result[0] < cut_off:
            print(file + " is an morepork")
            count_of_FN +=1
        else:
            print(file + " is a other")
            count_of_TN +=1
            
    print("cut_off set at ", cut_off)
    print("count_of_TP ", count_of_TP)
    print("count_of_FP ", count_of_FP)
    print("count_of_TN ", count_of_TN)
    print("count_of_FN ", count_of_FN)
    
    success_rate = (count_of_TP + count_of_TN)/ (count_of_TP + count_of_TN + count_of_FP + count_of_FN)
    
    print("success_rate ", success_rate)

def update_classify_march_test_data_using_tensorflow_model_with_probability():
    # I stuffed up the probability when I first classified March test data
    tensorflow_run_name = '2020_06_12_2'
    modelRunName = '2020_06_12_2'
    tensorflow_run_folder = base_folder + '/Audio_Analysis/audio_classifier_runs/tensorflow_runs' + '/' + tensorflow_run_name
    path_to_model = tensorflow_run_folder + "/model"
        
    reconstructed_model = tf.keras.models.load_model(path_to_model)        
    
    spectrogram_folder_path = base_folder + '/Audio_Analysis/temp'
    print(spectrogram_folder_path)
    if not os.path.exists(spectrogram_folder_path):
        os.makedirs(spectrogram_folder_path) 
        
    image_out_path_name = spectrogram_folder_path + "/" + 'temp.jpg'     

    cur = get_database_connection().cursor()
    cur.execute("SELECT ID, recording_id, startTime, duration, predictedByModel from model_run_result WHERE modelRunName = ? AND predictedByModel = ?", (modelRunName, "morepork_more-pork"))
    rows = cur.fetchall() 
    count_of_rows = len(rows)
    print("count_of_rows ", count_of_rows)
    count = 0
    
    for row in rows:
        count+=1
        print(count, ' of ', count_of_rows)
        model_run_result_ID = row[0]
        recording_id = row[1]
        startTime = row[2]
        duration = row[3]

        create_temp_single_focused_mel_spectrogram_for_tensorflow(recording_id, startTime, duration, image_out_path_name)
        
        # Now test spectrogram image against model
        img = tf.keras.preprocessing.image.load_img(image_out_path_name, target_size=[320, 240], color_mode="grayscale")
        x = tf.keras.preprocessing.image.img_to_array(img)        
        x = tf.keras.applications.mobilenet.preprocess_input(x[tf.newaxis,...])
        result = reconstructed_model(x)
        probability = str(result.numpy()[0][0]) # https://stackoverflow.com/questions/49568041/tensorflow-how-do-i-convert-a-eagertensor-into-a-numpy-array
        print("model_run_result_ID ", model_run_result_ID, " recording_id ", recording_id,  " startTime ", startTime, " has a  probability of ", probability)
        
        sql = "UPDATE model_run_result SET probability = ? WHERE ID = ?"            
        cur.execute(sql, (probability, model_run_result_ID))                
        get_database_connection().commit()
        
def test_sql_dates():
    cur = get_database_connection().cursor()
#     cur.execute("SELECT ID, recordingDateTimeNZ from test_data WHERE recordingDateTimeNZ BETWEEN ? AND ?", ("2020-03-01 02:23:01+13:00", "2020-03-30 00:41:29+13:00"))
    cur.execute("SELECT ID, recordingDateTime, recordingDateTimeNZ from onsets WHERE version = 7 AND recordingDateTimeNZ BETWEEN ? AND ? ORDER BY recordingDateTimeNZ", ("2020-03-01 00:00", "2020-03-31 23:59"))
    
    rows = cur.fetchall() 
    count_of_rows = len(rows)
    print("count_of_rows ", count_of_rows)
       
    for row in rows:
        recordingDateTime = row[1]
        recordingDateTimeNZ = row[2]
        print(recordingDateTime,recordingDateTimeNZ)
        
    
        
        