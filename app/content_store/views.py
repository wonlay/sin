import random, os, subprocess
from django.conf import settings
from django.http import HttpResponse
from django.template import loader
from django.http import Http404

import kafka

from content_store.models import ContentStore

from utils import json

from django.utils import simplejson
import shutil

running = {
}

kafkaHost = settings.KAFKA_HOST
kafkaPort = int(settings.KAFKA_PORT)

kafkaProducer = kafka.KafkaProducer(kafkaHost, kafkaPort)

def storeExists(request,store_name):
	resp = {
		'exists' : ContentStore.objects.filter(name=store_name).exists()
	}
	return HttpResponse(json.json_encode(resp))

def newStore(request,store_name):
	if ContentStore.objects.filter(name=store_name).exists():
		resp = {
			'ok' : False,
			'error' : 'store: %s already exists.' % store_name
		}
		return HttpResponse(json.json_encode(resp))
	desc = "test store"
	store = ContentStore(name=store_name,
		description=desc,
		sensei_port=random.randint(10000, 15000),
		broker_port=random.randint(15000, 20000))
	store.save()
	resp = {
		'ok' : True,
		'id': store.id,
		'name': store.name,
		'sensei_port': store.sensei_port,
		'broker_port': store.broker_port,
		'config': store.config,
		'created': store.created,
		'status': store.status,
	}
	return HttpResponse(json.json_encode(resp))

def deleteStore(request,store_name):
	if not ContentStore.objects.filter(name=store_name).exists():
		resp = {
			'ok' : False,
			'msg' : 'store: %s does not exist.' % store_name
		}
		return HttpResponse(json.json_encode(resp))
	killStore(store_name)

	store_data_dir = os.path.join(settings.STORE_HOME, store_name)
	try:
		shutil.rmtree(store_data_dir)
	except:
		pass
	ContentStore.objects.filter(name=store_name).delete()
	resp = {
		'ok' : True,
		'msg' : 'store: %s successfully deleted.' % store_name
	}
	return HttpResponse(json.json_encode(resp))

def updateConfig(request, store_name):
	config = request.POST.get('config');
	resp = {
		'ok': False,
	}
	if config:
		# TODO: valid configuration.
		ContentStore.objects.filter(name=store_name).update(config=config);
		resp['ok'] = True
	else:
		resp['error'] = 'No config provided.'

	return HttpResponse(json.json_encode(resp))

def addDoc(request,store_name):
	doc = request.POST.get('doc');
	
	if not doc:
		resp = {'ok':False,'error':'no doc posted'}
	else:
		try:
			jsonDoc = simplejson.loads(doc.encode('utf-8'))
			kafkaProducer.send([json.json_encode(jsonDoc)], store_name.encode('utf-8'))
			resp = {'ok': True,'numPosted':1}
		except ValueError:
			resp = {'ok':False,'error':'invalid json: %s' % doc}
		except Exception as e:
			resp = {'ok':False,'error':e}
	
	return HttpResponse(json.json_encode(resp))
	

def addDocs(request,store_name):
	docs = request.POST.get('docs');	
	if not docs:
		resp = {'ok':False,'error':'no docs posted'}
	else:
		try:
			jsonArray = simplejson.loads(docs.encode('utf-8'))
			messages = []
			for obj in jsonArray:
				str = json.json_encode(obj).encode('utf-8')
				messages.append(str)
			kafkaProducer.send(messages, store_name.encode('utf-8'))
			resp = {'ok':True,'numPosted':len(messages)}
		except ValueError:
			resp = {'ok':False,'error':'invalid json: %s' % docs}
		except Exception as e:
			resp = {'ok':False,'error':e}
	return HttpResponse(json.json_encode(resp))

def killStore(store_name):
	global running

	pid = running.get(store_name)
	if pid:
		os.system('kill %s' % pid)
		del running[store_name]
	
def stopStore(request, store_name):
	killStore(store_name)
	return HttpResponse(json.json_encode({'ok': True}))

def startStore(request, store_name):
	global running

	store = ContentStore.objects.get(name=store_name)

	classpath1 = os.path.join(settings.SENSEI_HOME, 'target/*')
	classpath2 = os.path.join(settings.SENSEI_HOME, 'target/lib/*')
	log4jclasspath = os.path.join(settings.SENSEI_HOME,'resources')
	webapp = os.path.join(settings.SENSEI_HOME,'src/main/webapp')

	classpath = "%s:%s:%s" % (classpath1,classpath2,log4jclasspath)

	store_home = os.path.join(settings.STORE_HOME, store_name)
	index = os.path.join(store_home, 'index')
	try:
		os.makedirs(index)
	except:
		pass
	conf = os.path.join(store_home, 'conf')
	try:
		os.makedirs(conf)
	except:
		pass
	logs = os.path.join(store_home, 'logs')
	try:
		os.makedirs(logs)
	except:
		pass

	sensei_properties = loader.render_to_string(
		'sensei-conf/sensei.properties', {
			'store': store,
			'index': index,
			'webapp': webapp,
		})
	sensei_custom_facets = loader.render_to_string(
		'sensei-conf/custom-facets.xml', {
		})
	sensei_plugins = loader.render_to_string(
		'sensei-conf/plugins.xml', {
		})

	out_file = open(os.path.join(conf, 'sensei.properties'), 'w+')
	try:
		out_file.write(sensei_properties)
		out_file.flush()
	finally:
		out_file.close()

	out_file = open(os.path.join(conf, 'custom-facets.xml'), 'w+')
	try:
		out_file.write(sensei_custom_facets)
		out_file.flush()
	finally:
		out_file.close()

	out_file = open(os.path.join(conf, 'schema.json'), 'w+')
	try:
		out_file.write(store.config)
		out_file.flush()
	finally:
		out_file.close()

	out_file = open(os.path.join(conf, 'plugins.xml'), 'w+')
	try:
		out_file.write(sensei_plugins)
		out_file.flush()
	finally:
		out_file.close()

	cmd = ["java", "-server", "-d64", "-Xmx1g", "-Xms1g", "-XX:NewSize=256m", "-classpath", classpath, "-Dlog.home=%s" % logs, "com.sensei.search.nodes.SenseiServer", conf]

	print ' '.join(cmd)

	p = subprocess.Popen(cmd, cwd=settings.SENSEI_HOME)
	running[store_name] = p.pid

	return HttpResponse(json.json_encode({'ok': True}))

def restartStore(request, store_name):
	stopStore(request, store_name)
	return startStore(request, store_name)

def getSize(request,store_name):
	resp = {'store':store_name,"size":0}
	return HttpResponse(json.json_encode(resp))
	
def getDoc(request,store_name,id):
	uid = long(id)
	doc = {'id':uid}
	resp = {'store':store_name,'doc':doc}
	return HttpResponse(json.json_encode(resp))

def available(request,store_name):
	if ContentStore.objects.filter(name=store_name).exists():
		resp = {'ok':True,'store':store_name,"available":True}
	else:
		resp = {'ok':False,'error':'store: %s does not exist.' % store_name}
	return HttpResponse(json.json_encode(resp))

def stores(request):
	objs = ContentStore.objects.all()
	resp = [{
			'id': store.id,
			'name': store.name,
			'sensei_port': store.sensei_port,
			'broker_port': store.broker_port,
			'config': store.config,
			'created': store.created,
			'description' : store.description,
			'status': store.status,
		}
		for store in objs]
	return HttpResponse(json.json_encode(resp))

