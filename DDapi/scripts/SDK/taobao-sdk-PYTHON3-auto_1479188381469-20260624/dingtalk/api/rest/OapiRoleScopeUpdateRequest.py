'''
Created by auto_sdk on 2025.12.02
'''
from dingtalk.api.base import RestApi
class OapiRoleScopeUpdateRequest(RestApi):
	def __init__(self,url=None):
		RestApi.__init__(self,url)
		self.dept_ids = None
		self.role_id = None
		self.userid = None

	def getHttpMethod(self):
		return 'POST'

	def getapiname(self):
		return 'dingtalk.oapi.role.scope.update'
