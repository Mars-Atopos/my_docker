'''
Created by auto_sdk on 2025.10.22
'''
from dingtalk.api.base import RestApi
class OapiMessageMassSendRequest(RestApi):
	def __init__(self,url=None):
		RestApi.__init__(self,url)
		self.allow_comment = None
		self.comment_type = None
		self.dep_id_list = None
		self.is_preview = None
		self.is_to_all = None
		self.media_id = None
		self.msg_body = None
		self.msg_type = None
		self.roleIds = None
		self.show_homepage = None
		self.text_content = None
		self.unionid = None
		self.userid_list = None
		self.uuid = None

	def getHttpMethod(self):
		return 'POST'

	def getapiname(self):
		return 'dingtalk.oapi.message.mass.send'
