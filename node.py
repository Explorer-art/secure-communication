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

port = server_port

clients = []

cache = []

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
		route_list.append(ip[0])
	
	return route_list

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
	now_date = get_now_date()

	if out_logging == True:
		print("[LOG] [" + now_date + "] " + message)

	file = open("log.txt", "a")
	file.write("[LOG] [" + now_date + "] " + message + "\n")
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

def check_route_list():
	while True:
		route_list = []

		file = open("route_list.txt", "r")
		lines = file.readlines()
		file.close()

		for line in lines:
			line = line.replace("\n", "")
			route_list.append(line)

def kick(client, address, reason):
	data = "REQUEST=KICKED:" + reason
	client.send(data.encode("utf-8"))
	client.close()

	log(f"{address[0]}:{address[1]} kicked for a reason: " + reason)

def send_all_nodes(data):
	nodes = get_route_list()
	for node in nodes:
		node_splited = node.split(":")
		ip = node_splited[0]
		port = int(node_splited[1])

		if ip == server_ip and port == server_port:
			continue

		try:
			client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			client.connect((ip, port))
			client.send(data)
			client.close()
		except:
			log(f"{ip}:{port} connect failed")

def send_all_clients(data): #Отправка сообщения всем пользователям
	for client in clients:
		client.send(data)

def handle(client, address): #Пользователь
	while True:
		try:
			data = client.recv(1024)

			send_all_clients(data)
			send_all_nodes(data)

			log(f"{address[0]}:{address[1]} send message")
		except:
			try:
				clients.remove(client)
				client.close()
			except:
				pass

			log(f"{address[0]}:{address[1]} disconnected")
			break

def server_handle(ip, port):
	global clients
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

		try:
			data = client.recv(1024)

			if len(data) > 35 and not data in cache:
				send_all_clients(data)
				send_all_nodes(data)
				cache.append(data)
				continue

			if data.decode("utf-8") == "REQUEST=USER_CONNECT":
				if client in clients:
					log(f"{address[0]}:{address[1]} already connected")
					kick(client, address, "You already connected!")

				client.send("REQUEST=SUCCESFUL_AUTH".encode("utf-8"))

				clients.append(client)

				threading.Thread(target=handle, daemon=True, args=(client, address)).start()
			elif data.decode("utf-8") == "REQUEST=GET_ROUTE_LIST":
				send_file(client, "route_list.txt")
				log(f"{address[0]}:{address[1]} get route list")
				client.close()
			elif data.decode("utf-8") == "REQUEST=ADD_NODE":
				log(f"{address[0]}:{address[1]} add node")
				add_node(address)
		except:
			pass

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

			message = message.split("//")[0]

			print("\n" + "[" + get_now_date() + "] " + message + "\n")
		except:
			pass

def writer(client, public_key):
	while True:
		message = input("\n> ")

		if message == "!info":
			print("Information:")
			print("Version: 1.0")
			print("")

		if message != "":
			message = f"{time.time()}//{username} > {message}"

			print("[" + get_now_date() + "] " + message)

			client.send(encrypt(public_key, message))

if os.path.isfile("route_list.txt") == False:
	file = open("route_list.txt", "w+")
	file.close()

if os.path.isfile("log.txt") == False:
	file = open("log.txt", "w+")
	file.close()

clear()

if server_switch == True:
	if server_ip == "":
		server_ip = get_ip()

		if server_ip == False:
			print("Error IP")

print("[LOG] Get route list..")
route_list = get_route_list()

if auto_update_route_list == True:
	print("[LOG] Update route list")

	if ip_connect_node == "":
		route = random.choice(route_list)
		route_splited = route.split(":")
		ip = route_splited[0]
		port = int(route_splited[1])
	else:
		ip = ip_connect_node
		port = port_connect_node

	print(f"[LOG] Connecting to {ip}:{port}..")

	p = update_route_list(ip, port)

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

	username = input("Enter username: ")

	if os.path.exists("private_key.txt") == False:
		print("[LOG] Generating encryption keys..")

		key = RSA.generate(2048)
		public_key = key.publickey().export_key()
		private_key = key.export_key()

		file = open(username + ".txt", "wb")
		file.write(public_key)
		file.close()

		file = open("private_key.txt", "wb")
		file.write(private_key)
		file.close()

	if os.path.exists(username + ".txt") == False:
		print(f"[ERROR] Username {username} not found!")
		sys.exit()

	if os.path.exists("friends") == False:
		os.mkdir("friends")

	friend_username = input("Enter username friend: ")

	try:
		file = open("friends/" + friend_username + ".txt", "rb")
		public_key = file.read()
		file.close()
	except:
		print("Error! Unknown username.")

	file = open("private_key.txt", "rb")
	private_key = file.read()
	file.close()

	if ip_connect_node == "":
		if auto_node_select == True:
			route = random.choice(route_list)
			route_splited = route.split(":")
			ip_node = route_splited[0]
			port_node = int(route_splited[1])
		elif auto_node_select == False:
			node = input("Enter the IP address of the server you want to connect: ")
			node_splited = node.split(":")
			ip_node = node_splited[0]
			port_node = int(node_splited[1])
	else:
		ip_node = ip_connect_node
		port_node = port_connect_node

	print(f"[LOG] Connecting to {ip_node}:{port_node}..")

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

	print("[LOG] Successful connection!")

	time.sleep(2)

	clear()

	print(f"""
		Welcome to Secure Communication!

		Your username: {username}
		Friend username: {friend_username}""")

	receive_thread = threading.Thread(target=receive, daemon=True, args=(client, private_key))  # Получение всех сообщений
	receive_thread.start()
	writer_thread = threading.Thread(target=writer, daemon=True, args=(client, public_key))  # Отправка сообщений
	writer_thread.start()

	while True:
		time.sleep(1)
else:
	out_logging = True
	server_handle(server_ip, port)
