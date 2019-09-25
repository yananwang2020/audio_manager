'''
Created on 5 Sep 2019

@author: tim
'''

#  https://www.youtube.com/watch?v=A0gaXfM1UN0&t=343s
# https://www.youtube.com/watch?v=D8-snVfekto
# How to Program a GUI Application (with Python Tkinter)!
# https://www.tutorialspoint.com/python3/python_gui_programming

HEIGHT = 600
WIDTH = 1400

import tkinter as tk
from tkinter import ttk
from tkinter import *
import os

# from gui_functions import *
import gui_functions

LARGE_FONT= ("Verdana", 12)


class Main_GUI(tk.Tk):
    # comment
    
    def __init__(self, *args, **kwargs):
        
        
        tk.Tk.__init__(self, *args, **kwargs)        
        tk.Tk.wm_title(self, "Cacophony Audio Manager")
        # https://stackoverflow.com/questions/47829756/setting-frame-width-and-height?rq=1
        container = tk.Frame(self,width=WIDTH, height=HEIGHT)
        container.grid_propagate(False)        
        container.pack(side="top", fill="both", expand=True)        
        container.grid_rowconfigure(0, weight = 1)
        container.grid_columnconfigure(0, weight = 1)
       
        self.frames = {}
        
        for F in (HomePage, SettingsPage, RecordingsPage, TaggingPage, ClipsPage, ArffPage, CreateWekaModelPage, EvaluateWekaModelPage):
        
            frame = F(container, self)
            self.frames[F] = frame
            
            frame.grid(row=0, column=0, sticky="nsew")
        
        self.show_frame(HomePage)
        
    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()
        
def qf(param):
    print(param)
        
class HomePage(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
       
        label = tk.Label(self, text="Home Page", font=LARGE_FONT)
        label.pack(pady=10,padx=10)
        
        settings_button = ttk.Button(self, text="Settings",
                            command=lambda: controller.show_frame(SettingsPage))    
        settings_button.pack()
        
        tagging_button = ttk.Button(self, text="Tagging",
                            command=lambda: controller.show_frame(TaggingPage))        
        tagging_button.pack()
        
        recordings_button = ttk.Button(self, text="Recordings",
                            command=lambda: controller.show_frame(RecordingsPage))        
        recordings_button.pack()
        
        clips_button = ttk.Button(self, text="Create audio clips",
                            command=lambda: controller.show_frame(ClipsPage))        
        clips_button.pack()
        
        arff_button = ttk.Button(self, text="Create Weka arff files",
                            command=lambda: controller.show_frame(ArffPage))        
        arff_button.pack()
        
        createWekaModelPage_button = ttk.Button(self, text="Create Weka Model",
                            command=lambda: controller.show_frame(CreateWekaModelPage))        
        createWekaModelPage_button.pack()
        
        evaluateWekaModelPage_button = ttk.Button(self, text="Evaluate Weka model",
                            command=lambda: controller.show_frame(EvaluateWekaModelPage))        
        evaluateWekaModelPage_button.pack()
        
class SettingsPage(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        
#         recordings_Folder = gui_functions.getRecordingsFolderWithOutHome()
        recordings_Folder = gui_functions.getRecordingsFolderWithOutHome()
        
        # https://www.python-course.eu/tkinter_entry_widgets.php        
        tk.Label(self,text="Recordings location").grid(column=0, columnspan=1, row=0)

        #https://stackoverflow.com/questions/16373887/how-to-set-the-text-value-content-of-an-entry-widget-using-a-button-in-tkinter
        entryText = tk.StringVar()
        recordings_folder_entry = tk.Entry(self, textvariable=entryText, width=80)
        recordings_folder_entry.grid(row=0, column=1, columnspan=1)
        entryText.set( recordings_Folder )
        

        tk.Button(self, 
                  text='Save', command=lambda: gui_functions.saveSettings(recordings_folder_entry.get())).grid(row=6, 
                                                               column=0, 
                                                               sticky=tk.W, 
                                                               pady=4)     

        tk.Button(self, 
                  text='Back to Home', 
                  command=lambda: controller.show_frame(HomePage)).grid(row=6, 
                                            column=1, 
                                            sticky=tk.W, 
                                            pady=4)                  

        
class TaggingPage(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        label = ttk.Label(self, text="Tagging Page", font=LARGE_FONT)
        label.pack(pady=10,padx=10)
        
        get_tags_button = ttk.Button(self, text="Get tags from server",
                            command=lambda: gui_functions.get_all_tags_for_all_devices_in_local_database())
        get_tags_button.pack()  
        
        button1 = ttk.Button(self, text="Back to Home",
                            command=lambda: controller.show_frame(HomePage))
        button1.pack() 
        
        

class RecordingsPage(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        title_label = ttk.Label(self, text="Recordings Page", font=LARGE_FONT)
#         label.pack(pady=10,padx=10)
        title_label.grid(column=0, columnspan=1, row=0)
        
        device_name_label = ttk.Label(self, text="Device name e.g fpF7B9AFNn6hvfVgdrJB").grid(column=0, columnspan=1, row=1)
             
        device_name = StringVar(value='fpF7B9AFNn6hvfVgdrJB')
        device_name_entry = tk.Entry(self,  textvariable=device_name, width=30).grid(column=1, columnspan=1, row=1)
        
        device_super_name_label = ttk.Label(self, text="Device Super name (e.g. Hammond Park").grid(column=2, columnspan=1, row=1)
        
        device_super_name = StringVar(value='Hammond Park')
        device_super_name_entry = tk.Entry(self,  textvariable=device_super_name, width=30).grid(column=3, columnspan=1,row=1)
       
        
        
        get_recordings_button = ttk.Button(self, text="Load Recordings from local folder",
                            command=lambda: gui_functions.load_recordings_from_local_folder(device_name.get(), device_super_name.get())).grid(column=0, columnspan=2, row=2)
#         get_recordings_button = ttk.Button(self, text="Load Recordings from local folder",
#                             command=lambda: gui_functions.load_recordings_from_local_folder(device_super_name.get())).grid(column=0, columnspan=1, row=2)
 

        get_recording_information_from_server_button = ttk.Button(self, text="Get Recording Information for recordings imported from local file system",
                            command=lambda: gui_functions.update_recording_information_for_all_local_database_recordings()).grid(column=0, columnspan=2, row=3)
              
        
        get_new_recordings_from_server_button = ttk.Button(self, text="Get New Recordings From Server",
                            command=lambda: gui_functions.get_recordings_from_server(device_name.get(), device_super_name.get())).grid(column=0, columnspan=2, row=4)
        get_new_recordings_from_server_label = ttk.Label(self, text="This will get the recordings for the device in the device name box. It will also assign a super name from the Super Name box").grid(column=2, columnspan=3, row=4)  
                                               
        
        scan_local_folder_for_recordings_not_in_local_db_and_update_button = ttk.Button(self, text="Scan recordings folder for recordings not in local db and update",
                            command=lambda: gui_functions.scan_local_folder_for_recordings_not_in_local_db_and_update(device_name.get(), device_super_name.get())).grid(column=0, columnspan=2, row=5)
                                                
        scan_label = ttk.Label(self, text="If you do NOT know the device name or super name enter unknown in the fields. The device name will be updated automatically").grid(column=2, columnspan=3, row=5)                   
                       
        
        back_to_home_button = ttk.Button(self, text="Back to Home",
                            command=lambda: controller.show_frame(HomePage)).grid(column=0, columnspan=1, row=6)
        
class ClipsPage(tk.Frame):
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        
        unique_tags = gui_functions.get_unique_whats_from_local_db()
                
        title_label = ttk.Label(self, text="Clips Page", font=LARGE_FONT)
        title_label.grid(column=0, columnspan=1, row=0)        
              
        device_super_name_label = ttk.Label(self, text="Device Super name (e.g. Hammond Park)").grid(column=0, columnspan=1, row=1)        
        device_super_name = StringVar(value='Hammond Park')
        device_super_name_entry = tk.Entry(self,  textvariable=device_super_name, width=30).grid(column=1, columnspan=1,row=1)
        
        what_label = ttk.Label(self, text="What (e.g. more pork - classic)").grid(column=0, columnspan=1, row=2)      
                                    
        what = StringVar()
        what_combo = ttk.Combobox(self, textvariable=what, values=unique_tags)
        what_combo.current(0)
        what_combo.grid(column=1, columnspan=1,row=2) 
                
                
        version_label = ttk.Label(self, text="Versions (e.g. morepork_base)").grid(column=0, columnspan=1, row=3)        
        version = StringVar(value='morepork_base')
        version_entry = tk.Entry(self,  textvariable=version, width=30).grid(column=1, columnspan=1,row=3)
        
        
        run_base_folder_label = ttk.Label(self, text="Base folder for output (e.g. /home/tim/Work/Cacophony/Audio_Analysis/audio_classifier_runs)").grid(column=0, columnspan=1, row=4)           
        run_base_folder_folder = StringVar(value='/home/tim/Work/Cacophony/Audio_Analysis/audio_classifier_runs')
        run_base_folder_entry = tk.Entry(self,  textvariable=run_base_folder_folder, width=110).grid(column=1, columnspan=1,row=4) 
        
        run_folder_label = ttk.Label(self, text="Output (sub)folder where clips will be created (e.g. 2019_09_17_1).").grid(column=0, columnspan=1, row=5)    
        run_folder = StringVar(value='2019_09_17_1')
        run_folder_entry = tk.Entry(self,  textvariable=run_folder, width=110).grid(column=1, columnspan=1,row=5) 
        
        
#         create_clips_button = ttk.Button(self, text="Create Clips",
#                             command=lambda: gui_functions.create_clips(device_super_name.get(), what.get(), version.get(), run_base_folder_folder.get(),run_folder.get() )).grid(column=0, columnspan=2, row=6)
# 
        create_clips_button = ttk.Button(self, text="Create Clips",
                            command=lambda: gui_functions.create_clips(device_super_name.get(), what.get(), version.get(), run_base_folder_folder.get(),run_folder.get() )).grid(column=0, columnspan=2, row=6)

                 
        back_to_home_button = ttk.Button(self, text="Back to Home",
                            command=lambda: controller.show_frame(HomePage)).grid(column=0, columnspan=1, row=7)

                
class ArffPage(tk.Frame):
    
    
    def choose_clip_folder(self, base_folder, run_folder):
        choosen_folder = gui_functions.choose_clip_folder(base_folder, run_folder)
        # https://stackoverflow.com/questions/50227577/update-label-in-tkinter-when-calling-function
        self.clip_folder.set(choosen_folder)
        
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.clip_folder = StringVar(value='')
        openSmile_config_files = gui_functions.getOpenSmileConfigFiles()
        arffTemplateFiles = gui_functions.getArffTemplateFiles()
             
        title_label = ttk.Label(self, text="Create Arff Page", font=LARGE_FONT)
        title_label.grid(column=0, columnspan=1, row=0)    
        
        base_folder_label = ttk.Label(self, text="Base folder (e.g. /home/tim/Work/Cacophony/Audio_Analysis/audio_classifier_runs)").grid(column=0, columnspan=1, row=1)        
        base_folder = StringVar(value='/home/tim/Work/Cacophony/Audio_Analysis/audio_classifier_runs')
        base_folder_entry = tk.Entry(self,  textvariable=base_folder, width=80).grid(column=1, columnspan=1,row=1)    
        
        run_folder_label = ttk.Label(self, text="Run folder (e.g. 2019_09_17_1)").grid(column=0, columnspan=1, row=2)    
        run_folder = StringVar(value='2019_09_17_1')
        run_folder_entry = tk.Entry(self,  textvariable=run_folder, width=80).grid(column=1, columnspan=1,row=2) 
        

        choose_clip_folder_button = ttk.Button(self, text="Choose clip folder",
                            command=lambda: self.choose_clip_folder(base_folder.get(), run_folder.get())).grid(column=0, columnspan=1, row=3)
        self.clip_folder_entry = tk.Entry(self,  textvariable=self.clip_folder, width=80).grid(column=1, columnspan=1,row=3)  

          
        openSmile_config_file_label = ttk.Label(self, text="Name of openSMILE configuration file (e.g. morepork_unknown_label_morpork.conf)").grid(column=0, columnspan=1, row=4)      
        openSmile_config_file = StringVar()
        openSmile_config_combo = ttk.Combobox(self, textvariable=openSmile_config_file, values=openSmile_config_files, width=80)
        openSmile_config_combo.current(0)
        openSmile_config_combo.grid(column=1, columnspan=2,row=4) 
        
        create_arff_button = ttk.Button(self, text="Create Individual Arff Files for each audio file",
                            command=lambda: gui_functions.create_arff_file(base_folder.get(), run_folder.get(), self.clip_folder.get(), openSmile_config_file.get())).grid(column=0, columnspan=1, row=5)
          
        arff_template_file_label = ttk.Label(self, text="Name of openSMILE template arff file (e.g. arff_template.mfcc.arff)").grid(column=0, columnspan=1, row=6)     
        arff_template_file = StringVar()
        arff_template_combo = ttk.Combobox(self, textvariable=arff_template_file, values=arffTemplateFiles, width=80)
        arff_template_combo.current(0)
        arff_template_combo.grid(column=1, columnspan=2,row=6)

        
        merge_arffs_button = ttk.Button(self, text="Merge Arffs",
                            command=lambda: gui_functions.merge_arffs(base_folder.get(), run_folder.get(), arff_template_file.get())).grid(column=0, columnspan=1, row=7)
        
        back_to_home_button = ttk.Button(self, text="Back to Home",
                            command=lambda: controller.show_frame(HomePage)).grid(column=0, columnspan=1, row=8)   
                            
class CreateWekaModelPage(tk.Frame):    
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.clip_folder = StringVar(value='')
        openSmile_config_files = gui_functions.getOpenSmileConfigFiles()
        arffTemplateFiles = gui_functions.getArffTemplateFiles()
             
        title_label = ttk.Label(self, text="Using Weka", font=LARGE_FONT)
        title_label.grid(column=0, columnspan=1, row=0)   
        
        weka_instructions = "To create a Weka model you will need to use the Weka program https://www.cs.waikato.ac.nz/ml/weka/downloading.html\n\
        Once Weka has been installed, you can run it from the weka directory (e.g. weka-3-8-3) using the command weka - jar weka.jar\n\
        These instructions are for how I originally used Weka, but may change in future.\n\
        In Weka, open Explorer, open the merged arff file that you previously created and stored (e.g. at /home/tim/Work/Cacophony/Audio_Analysis/audio_classifier_runs/mfcc_merge_morepork_unknown.arff)\
        Change to the Classify tab, press the choose button and select the model type e.g. Trees LMT.\
        Choose Cross validation, folds 10. Press the start button.\n\
        When finished, right click on the result and choose 'Save Model (e.g. in ... audio_classifier_runs/2019-09-17-1/model_run/model) The file extension is automatically .model.\n\
        You can now use this model in the next page"
        msg = tk.Message(self, text = weka_instructions)
        msg.config(bg='lightgreen', font=('times', 16), width=1200)
        msg.grid(column=0, columnspan=6, row=1)    
        
        
        back_to_home_button = ttk.Button(self, text="Back to Home",
                            command=lambda: controller.show_frame(HomePage)).grid(column=0, columnspan=1, row=8)                
        
class EvaluateWekaModelPage(tk.Frame):
    
    
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.clip_folder = StringVar(value='')
        openSmile_config_files = gui_functions.getOpenSmileConfigFiles()
        arffTemplateFiles = gui_functions.getArffTemplateFiles()
             
        title_label = ttk.Label(self, text="Evaluate a Weka model", font=LARGE_FONT)
        title_label.grid(column=0, columnspan=1, row=0)    
        
        weka_instructions = "The Weka model was created using arff files.  You can now run the model against the same training arff files \
        and save the results in the database.  Because the training arff files contained the expected result, you will be able to look at \
        individual instances to determine if the model got it correct.  You will be able to update the tag in the database with your new \
        determination."
        msg = tk.Message(self, text = weka_instructions)
        msg.config(bg='lightgreen', font=('times', 16), width=1200)
        msg.grid(column=0, columnspan=6, row=1)   
        
        base_folder_label = ttk.Label(self, text="Base folder (e.g. /home/tim/Work/Cacophony/Audio_Analysis/audio_classifier_runs)").grid(column=0, columnspan=1, row=2)        
        base_folder = StringVar(value='/home/tim/Work/Cacophony/Audio_Analysis/audio_classifier_runs')
        base_folder_entry = tk.Entry(self,  textvariable=base_folder, width=80).grid(column=1, columnspan=1,row=2)    
        
        run_folder_label = ttk.Label(self, text="Run folder (e.g. 2019_09_17_1)").grid(column=0, columnspan=1, row=3)    
        run_folder = StringVar(value='2019_09_17_1')
        run_folder_entry = tk.Entry(self,  textvariable=run_folder, width=80).grid(column=1, columnspan=1,row=3) 
        
        arff_folder_label = ttk.Label(self, text="Arff folder - that has the same arff files that were used to create this model (e.g. )").grid(column=0, columnspan=1, row=4)    
        arff_folder = StringVar(value='arff_files')
        arff_folder_entry = tk.Entry(self,  textvariable=arff_folder, width=80).grid(column=1, columnspan=1,row=4) 
        
        modelRunName_label = ttk.Label(self, text="Model run name (usually same as run folder e.g. 2019_09_17_1)").grid(column=0, columnspan=1, row=5)    
        modelRunName = StringVar(value='2019_09_17_1')
        modelRunName_entry = tk.Entry(self,  textvariable=modelRunName, width=80).grid(column=1, columnspan=1,row=5) 
        
        evaluate_button = ttk.Button(self, text="Evaluate Model",
                            command=lambda: gui_functions.process_arff_folder(base_folder.get(), run_folder.get(), arff_folder.get(), modelRunName.get())).grid(column=0, columnspan=1, row=7)
        
        sqlite_instructions = "Once you have completed the previous step, use the separate 'DB Browser for SQLite' program to find interesting examples by using the 'Browse Data' tab in the 'model_run_result' table.\
        For example, can filter the results, by typing unknown in the actual column filter, and morepork in the predictedByModel column filter.\
        Then enter the enter recording id and start time in the fields below to play that clip"
        msg = tk.Message(self, text = sqlite_instructions)
        msg.config(bg='lightgreen', font=('times', 16), width=1200)
        msg.grid(column=0, columnspan=6, row=8)   
        
        recording_id_label = ttk.Label(self, text="Recording ID (e.g. 240631").grid(column=0, columnspan=1, row=9)        
        recording_id = StringVar(value='240631')
        recording_id_entry = tk.Entry(self,  textvariable=recording_id, width=80).grid(column=1, columnspan=1,row=9)   
        
        start_time_label = ttk.Label(self, text="Start time (seconds) (e.g. 4.2").grid(column=0, columnspan=1, row=10)        
        start_time = StringVar(value='4.2')
        start_time_entry = tk.Entry(self,  textvariable=start_time, width=80).grid(column=1, columnspan=1,row=10) 
        
        duration_label = ttk.Label(self, text="Duration (seconds) e.g. 1.5").grid(column=0, columnspan=1, row=11)        
        duration = StringVar(value='1.5')
        duration_entry = tk.Entry(self,  textvariable=duration, width=80).grid(column=1, columnspan=1,row=11)  
        
        play_clip_button = ttk.Button(self, text="Play clip",
                            command=lambda: gui_functions.play_clip(recording_id.get(), start_time.get(), duration.get())).grid(column=0, columnspan=1, row=12)
         
 

        back_to_home_button = ttk.Button(self, text="Back to Home",
                            command=lambda: controller.show_frame(HomePage)).grid(column=0, columnspan=1, row=15)                
               
        
app = Main_GUI()
app.mainloop() 