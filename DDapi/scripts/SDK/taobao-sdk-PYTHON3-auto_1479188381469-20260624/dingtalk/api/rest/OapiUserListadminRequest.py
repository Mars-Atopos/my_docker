'''
Created by auto_sdk on 2026.06.01
'''
from dingtalk.api.base import RestApi
class OapiUserListadminRequest(RestApi):
	def __init__(self,url=None):
		RestApi.__init__(self,url)
		self.permissionCode = None

	def getHttpMethod(self):
		return 'POST'

	def getapiname(self):
		return 'dingtalk.oapi.user.listadmin'
