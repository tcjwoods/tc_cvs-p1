import paho.mqtt.client as mqtt


def on_message(client, userdata, msg):
    print("Topic: ", msg.topic)
    f = open("Temp/cvs_image_temp.jpg", "wb")
    f.write(msg.payload)
    f.close()
    print("Image saved.\n")


client = mqtt.Client()
client.on_message = on_message
client.connect("192.168.42.10", 1883)
client.subscribe("/data/LI")
client.loop_forever()
