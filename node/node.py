import os
import sys
import time
import datetime
import json
import random
import struct
import hashlib
import socket
import requests
import threading
from config import *
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import PKCS1_OAEP

port = 27575

number_maximum_length = 64

numbers = []
clients = []
addresses = []
numbers_connect = []

def clear():
	if sys.platform == "win32":
		os.system("cls")
	elif sys.platform == "linux" or sys.platform == "linux2":
		os.system("clear")

def generate_random_string(length):
	chars = "qwertyuiopasdfghjklzxcvbnm1234567890"
	random_string = "".join(random.choices(chars, k=length))
	return random_string

def send_file(sck: socket.socket, filename):
	filesize = os.path.getsize(filename)
	sck.sendall(struct.pack("<Q", filesize))

	file = open(filename, "rb")

	while read_bytes := file.read(1024):
		sck.sendall(read_bytes)

def receive_file_size(sck: socket.socket):
	fmt = "<Q"
	expected_bytes = struct.calcsize(fmt)
	received_bytes = 0
	stream = bytes()

	while received_bytes < expected_bytes:
		chunk = sck.recv(expected_bytes - received_bytes)
		stream += chunk
		received_bytes += len(chunk)

	filesize = struct.unpack(fmt, stream)[0]
	return filesize

def receive_file(sck: socket.socket, filename):
	filesize = receive_file_size(sck)

	file = open(filename, "wb")
	received_bytes = 0

	while received_bytes < filesize:
		chunk = sck.recv(1024)
		if chunk:
			file.write(chunk)
			received_bytes += len(chunk)

def get_route_list():
	route_list = []

	file = open("route_list.txt", "r")
	lines = file.readlines()
	file.close()

	for line in lines:
		line = line.replace("\n", "")
		ip = line.split(" ")
		route_list.append(ip)
	
	return route_list

def get_banned_ips():
	banned_ips = []

	file = open("banned_ips.txt", "r")
	lines = file.readlines()
	file.close()

	for line in lines:
		banned_ip = line.replace("\n", "")
		banned_ips.append(banned_ip)
	
	return banned_ips

def get_now_date():
	now = datetime.datetime.now()
	return f"{now.day}-{now.month}-{now.year} {now.hour}:{now.minute}:{now.second}"

def get_ip():
	try:
		ip = requests.get("https://ident.me").content.decode()
		return ip
	except:
		return False

def log(message):
	if out_logging == True:
		print("[LOG] [" + get_now_date() + "] " + message)

	file = open("log.txt", "a")
	file.write("[LOG] [" + get_now_date() + "] " + message + "\n")
	file.close()

def update_route_list(ip, port):
	try:
		client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client.connect((ip, port))

		client.send("REQUEST=GET_ROUTE_LIST".encode("utf-8"))

		receive_file(client, "route_list.txt")

		client.close()

		return True
	except:
		return False

def add_node(address):
	file = open("route_list.txt", "a")
	file.write(f"{address[0]}:{address[1]} " + datetime.datetime.now())
	file.close()

def check_number(number):
	for ip in route_list:
		try:
			if ip == server_ip:
				continue
			
			client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			client.connect((ip, port))

			data = "REQUEST=CHECK_NUMBER:" + number

			client.send(data.encode("utf-8"))

			data = client.recv(1024).decode("utf-8")

			if data == "REQUEST=TRUE":
				return ip
		except:
			return False
		
	return False

def send_node(ip, number, mode, message):
	try:
		client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client.connect((ip, port))

		data = "REQUEST=SEND_NODE:" + mode

		client.send(data.encode("utf-8"))

		client.send(number.encode("utf-8"))

		client.send(message)

		data = client.recv(1024)

		client.close()

		if data == "REQUEST=OKAY":
			return True
		elif data == "REQUEST=NOT_FOUND":
			return False
	except:
		return False

def kick(client, address, reason):
	data = "REQUEST=KICKED:" + reason
	client.send(data.encode("utf-8"))
	client.close()

	log(f"{address[0]}:{address[1]} kicked for a reason: " + reason)

def ban(client, address, reason):
	file = open("banned_ip.txt", "a")
	file.write(address[0] + "\n")
	file.close()

	kick(client, address, "You have been banned!")

	log(f"{address[0]}:{address[1]} banned for a reason: " + reason)

def amount(): #Количество подключённых пользователей
	amount = 0

	for client in clients:
		amount += 1

	return amount

def list(): #Список подключённых пользователей
	for number in numbers:
		log(number + ", ", end="")

def send_message(message, number_connect): #Отправка сообщения отдельному пользователю
	try:
		if number_connect in numbers:
			number_connect_index = numbers.index(number_connect)
			client_data = clients[number_connect_index]
			client_data.send(message)
	except Exception as error:
		print(error)

def broadcast(message): #Отправка сообщения всем пользователям
	for client in clients:
		client.send(message.encode("utf-8"))

	log("Broadcast message sended")

def handle(client, address): #Пользователь
	global numbers_connect
	try:
		public_key = client.recv(4096)

		number = hashlib.sha256(public_key).hexdigest()

		data = client.recv(1024).decode("utf-8")

		number_lenght = len(data)

		if number_lenght == number_maximum_length: #Проверка длины номера
			number_connect = data
			numbers_connect.append(number_connect)
		else:
			kick(client, address, "The number is too long or short!")

		client.send("REQUEST=WAITING".encode("utf-8"))

		ip_server_connect = ""

		check_n = False

		while True:
			try:
				if number in numbers_connect:
					if number_connect in numbers_connect:
						check_n = True
						break
					else:
						ip_server_connect = check_number(number_connect)

						if ip_server_connect != False:
							check_n = True
							break
			except Exception as error:
				print(error)
		
		if check_n == True:
			client.send("REQUEST=SUCCESFUL_CHANNEL_CREATED".encode("utf-8"))

			numbers.append(number)
			clients.append(client)
			addresses.append(address)
		
		time.sleep(1)
		
		if number_connect in numbers:
			number_connect_index = numbers.index(number_connect)
			client_data = clients[number_connect_index]
			client_data.send(public_key)
		else:
			if ip_server_connect != "":
				send_node(ip_server_connect, number_connect, "KEY", public_key)
		
		log(f"{address[0]}:{address[1]} connected to channel")
	except:
		log(f"{address[0]}:{address[1]} disconnected")

		try:
			numbers.remove(number)
			clients.remove(client)
			addresses.remove(address)
			client.close()
		except:
			pass

		return False

	while True:
		try:
			message = client.recv(1024)

			if ip_server_connect == "":
				send_message(message, number_connect)
			else:
				send_node(ip_server_connect, number_connect, "MESSAGE", message)
		except:
			log(f"{address[0]}:{address[1]} disconnected")

			try:
				numbers.remove(number)
				clients.remove(client)
				addresses.remove(address)
				client.close()
			except:
				pass

			break

def check_route_list():
	while True:
		route_list = get_route_list()
		pass

def server_handle(ip, port):
	log("Started server..")

	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind((ip, port))
	server.listen()

	log("Server started!")
	log("IP: " + ip)
	log("PORT: " + str(port))

	while True: #Основной цикл сервера
		client, address = server.accept()

		log(f"{address[0]}:{address[1]} connected ")

		data = client.recv(1024).decode("utf-8")

		if data == "REQUEST=USER_CONNECT":
			if address[0] in banned_ips:
				kick(client, address, "You have been banned!")
			elif address in addresses:
				log(f"{address[0]}:{address[1]} already connected")
				kick(client, address, "You already connected!")

			client.send("REQUEST=SUCCESFUL_AUTH".encode("utf-8"))

			threading.Thread(target=handle, daemon=True, args=(client, address)).start()
		elif data == "REQUEST=GET_ROUTE_LIST":
			send_file(client, "route_list.txt")
			log(f"{address[0]}:{address[1]} get route list")
			client.close()
		elif data[0:20] == "REQUEST=CHECK_NUMBER":
			log(f"{address[0]}:{address[1]} check number")
			number = data[21:21 + number_maximum_length]

			if len(number) != number_maximum_length:
				client.send("REQUEST=ERROR_NUMBER_LENGTH".encode("utf-8"))
				client.close()
				log("Error number length")
			
			if number in numbers_connect:
				client.send("REQUEST=TRUE".encode("utf-8"))
				client.close()
				log(f"{address[0]}:{address[1]} check number: TRUE")
			else:
				client.send("REQUEST=FALSE".encode("utf-8"))
				client.close()
				log(f"{address[0]}:{address[1]} check number: FALSE")
		elif data == "REQUEST=SEND_NODE:KEY":
			log(f"{address[0]}:{address[1]} send node key")
			number = client.recv(1024).decode("utf-8")

			public_key = client.recv(4096)

			if number in numbers:
				number_index = numbers.index(number)
				client_data = clients[number_index]
				client_data.send(public_key)

				client.send("REQUEST=OKAY".encode("utf-8"))
			else:
				client.send("REQUEST=NOT_FOUND".encode("utf-8"))
			
			client.close()
		elif data == "REQUEST=SEND_CODE:MESSAGE":
			number = client.recv(1024).decode("utf-8")

			message = client.recv(4096)

			if number in numbers:
				number_index = numbers.index(number)
				client_data = clients[number_index]
				client_data.send(message)

				client.send("REQUEST=OKAY".encode("utf-8"))
			else:
				client.send("REQUEST=NOT_FOUND".encode("utf-8"))
			
			client.close()
		elif data == "REQUEST=ADD_NODE":
			log(f"{address[0]}:{address[1]} add node")
			add_node(address)

def encrypt(public_key, message):
	key = RSA.import_key(public_key)
	cipher = PKCS1_OAEP.new(key)
	encrypted_message = cipher.encrypt(message.encode("utf-8"))
	return encrypted_message

def decrypt(private_key, encrypted_message):
	key = RSA.import_key(private_key)
	cipher = PKCS1_OAEP.new(key)
	message = cipher.decrypt(encrypted_message)
	return message

def receive(client, private_key):
	while True:
		try:
			message = decrypt(private_key, client.recv(1024)).decode("utf-8")

			print("\n" + "[" + get_now_date() + "] " + message + "\n")
		except Exception as error:
			print("Error! " + str(error))
			client.close()
			break

def writer(client, public_key):
	while True:
		message = input("\n> ")

		if message == "!info":
			print("Информация:")
			print("Версия: 1.0")
			print("")

		if message != "":
			message = f"{number} {username} > {message}"

			print("[" + get_now_date() + "] " + message)

			client.send(encrypt(public_key, message))

if os.path.isfile("route_list.txt") == False:
	file = open("route_list.txt", "w+")
	file.close()

if os.path.isfile("log.txt") == False:
	file = open("log.txt", "w+")
	file.close()

if os.path.isfile("banned_ips.txt") == False:
	file = open("banned_ips.txt", "w+")
	file.close()

banned_ips = get_banned_ips()

clear()

if os.path.isfile("public_key.txt") == False or os.path.isfile("private_key.txt") == False and client_switch == True:
	print("[LOG] Generating encryption keys..")

	key = RSA.generate(2048)
	public_key = key.publickey().export_key()
	private_key = key.export_key()

	file = open("public_key.txt", "wb")
	file.write(public_key)
	file.close()

	file = open("private_key.txt", "wb")
	file.write(private_key)
	file.close()

if client_switch == True:
	file = open("public_key.txt", "rb")
	public_key_1 = file.read()
	file.close()

	file = open("private_key.txt", "rb")
	private_key = file.read()
	file.close()

if server_switch == True:
	if server_ip == "":
		server_ip = get_ip()

		if server_ip == False:
			server_ip = input("Enter server IP: ")

print("[LOG] Get route list..")
route_list = get_route_list()

if auto_update_route_list == True:
	print("[LOG] Update route list")

	ip_route = random.choice(route_list)

	print(f"[LOG] Connecting to {ip_route}:{port}..")

	p = update_route_list(ip_route, port)

	if p == True:
		print("[LOG] Updated route list")
	
		route_list = get_route_list()
	else:
		print("[ERROR] Update routed list failed")

if client_switch == True:
	if server_switch == True:
		print("[LOG] Starting server..")

		out_logging = False
		threading.Thread(target=server_handle, daemon=True, args=(server_ip, port)).start()

		print("[LOG] Server started")

	username = input("Enter the user name: ")

	if auto_node_select == True:
		ip_node = random.choice(route_list)
	elif auto_node_select == False:
		if ip_connect_node == "":
			ip_node = input("Enter the IP address of the server you want to connect: ")
		else:
			ip_node = ip_connect_node

	print(f"[LOG] Connecting to {ip_node}:{port}..")

	client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	client.connect((ip_node, port))

	print(f"[LOG] Connected to {ip_node}:{port}")

	print("[LOG] Authorization..")

	client.send("REQUEST=USER_CONNECT".encode("utf-8"))

	data = client.recv(1024).decode("utf-8")

	if data[0:14] == "REQUEST=KICKED":
		reason = data[15:9999]
		print("You are kicked for a reason: " + reason)

		client.close()

		sys.exit()
	elif data == "REQUEST=SUCCESFUL_AUTH":
		print("[LOG] Authorization has been successfully completed!")
	
	number = hashlib.sha256(public_key_1).hexdigest()
	
	print("Your number: " + number)

	client.send(public_key_1)

	number_connect = input("Enter the number of the user you want to connect: ")

	client.send(number_connect.encode("utf-8"))

	data = client.recv(1024).decode("utf-8")

	if data[0:14] == "REQUEST=KICKED":
		reason = data[15:9999]
		print("You are kicked for a reason: " + reason)

		client.close()

		sys.exit()

	if data == "REQUEST=WAITING":
		print("Waiting for the user to connect..")

		data = client.recv(1024).decode("utf-8")

	if data == "REQUEST=SUCCESFUL_CHANNEL_CREATED":
		public_key_2 = client.recv(4096)

		print("[LOG] Successful connection!")

		time.sleep(2)

		clear()

		print("Secure Communication Channel")
		print("")
		print("Your username: " + username)
		print("Your number: " + number)
		print("")

		receive_thread = threading.Thread(target=receive, daemon=True, args=(client, private_key))  # Получение всех сообщений
		receive_thread.start()
		writer_thread = threading.Thread(target=writer, daemon=True, args=(client, public_key_2))  # Отправка сообщений
		writer_thread.start()

	while True:
		time.sleep(1)
else:
	out_logging = True
	server_handle(server_ip, port)
