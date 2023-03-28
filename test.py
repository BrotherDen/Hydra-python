import mysql.connector
import serial
from tkinter import *
import configparser

def start():
    ser = serial.Serial(port_name.get(), 9600)
    while True:
        data = ser.readline().decode('utf-8').strip()
        print(data)
        try:
            cursor.execute("INSERT INTO {} (value) VALUES (%s)".format(table_name.get()), (data,))
            cnx.commit()
        except mysql.connector.Error as err:
            print("Something went wrong: {}".format(err))

def stop():
    ser.close()
    cursor.close()
    cnx.close()

def save_settings():
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'server_name': server_name.get(),
        'database_name': database_name.get(),
        'table_name': table_name.get(),
        'user_name': user_name.get(),
        'password': password.get(),
        'port_name': port_name.get()
    }
    with open('settings.ini', 'w') as f:
        config.write(f)

def load_settings():
    try:
        config = configparser.ConfigParser()
        config.read('settings.ini')
        server_name.insert(0, config['DEFAULT']['server_name'])
        database_name.insert(0, config['DEFAULT']['database_name'])
        table_name.insert(0, config['DEFAULT']['table_name'])
        user_name.insert(0, config['DEFAULT']['user_name'])
        password.insert(0, config['DEFAULT']['password'])
        port_name.insert(0, config['DEFAULT']['port_name'])
    except FileNotFoundError:
        pass

try:
    cnx = mysql.connector.connect(user=user_name.get(), password=password.get(),
                                  host=server_name.get(),
                                  database=database_name.get())
except mysql.connector.Error as err:
    print("Something went wrong: {}".format(err))
else:
    cursor = cnx.cursor()

root = Tk()

server_label = Label(root, text="Server name:")
server_label.pack()
server_name = Entry(root)
server_name.pack()
server_name.insert(0, "localhost")

database_label = Label(root, text="Database name:")
database_label.pack()
database_name = Entry(root)
database_name.pack()
database_name.insert(0, "mydatabase")

table_label = Label(root, text="Table name:")
table_label.pack()
table_name = Entry(root)
table_name.pack()
table_name.insert(0, "mytable")

user_label = Label(root, text="User name:")
user_label.pack()
user_name = Entry(root)
user_name.pack()
user_name.insert(0, "root")

password_label = Label(root, text="Password:")
password_label.pack()
password = Entry(root, show="*")
password.pack()
password.insert(0, "")

port_label = Label(root, text="Port name:")
port_label.pack()
port_name = Entry(root)
port_name.pack()
port_name.insert(0, "COM5")

start_button = Button(root, text="Start", command=start)
start_button.pack()
stop_button = Button(root, text="Stop", command=stop)
stop_button.pack()

save_button = Button(root, text="Save settings", command=save_settings)
save_button.pack()

load_settings()

root.mainloop()