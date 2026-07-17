'''
Created by auto_sdk on 2024.10.10
'''
from dingtalk.api.base import RestApi
class OapiAttendanceGetattcolumnsRequest(RestApi):
	def __init__(self,url=None):
		RestApi.__init__(self,url)

	def getHttpMethod(self):
		return 'POST'

	def getapiname(self):
		return 'dingtalk.oapi.attendance.getattcolumns'
