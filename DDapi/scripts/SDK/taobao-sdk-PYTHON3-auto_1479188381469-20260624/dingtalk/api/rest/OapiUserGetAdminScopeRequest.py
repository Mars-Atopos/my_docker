'''
Created by auto_sdk on 2026.06.01
'''
from dingtalk.api.base import RestApi
class OapiUserGetAdminScopeRequest(RestApi):
	def __init__(self,url=None):
		RestApi.__init__(self,url)
		self.permissionCode = None
		self.userid = None

	def getHttpMethod(self):
		return 'POST'

	def getapiname(self):
		return 'dingtalk.oapi.user.get_admin_scope'
