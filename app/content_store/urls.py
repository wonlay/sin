from django.conf.urls.defaults import patterns, include, url

urlpatterns = patterns('content_store.views',
  (r'^new-store/(?P<store_name>[^/]+)/?$','newStore'),
  (r'^open-store/(?P<store_name>[^/]+)/?$','openStore'),
  (r'^delete-store/(?P<store_name>[^/]+)/?$','deleteStore'),
  (r'^exists/(?P<store_name>[^/]+)/?$','storeExists'),
  (r'^update-config/(?P<store_name>[^/]+)/?$','updateConfig'),
  (r'^addDoc/(?P<store_name>[^/]+)/?$','addDoc'),
  (r'^addDocs/(?P<store_name>[^/]+)/?$','addDocs'),
  (r'^start-store/(?P<store_name>[^/]+)/?$','startStore'),
  (r'^stop-store/(?P<store_name>[^/]+)/?$','stopStore'),
  (r'^restart-store/(?P<store_name>[^/]+)/?$','restartStore'),
  (r'^get-size/(?P<store_name>[^/]+)/?$','getSize'),
  (r'^get-doc/(?P<id>\d+)/(?P<store_name>[^/]+)/?$','getDoc'),
  (r'^available/(?P<store_name>[^/]+)/?$','available'),
  (r'^stores/?$','stores'),
)