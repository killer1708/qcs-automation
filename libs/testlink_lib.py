#! /usr/bin/python
# -*- coding: UTF-8 -*-


"""
Testlink  
Created on 29 may. 2018
@author: Vitthal Padwal(vitthal.padwal@msyste) 

Calling Testlink API for getting/modifying qnap testcases.
"""

from __future__ import print_function
import testlink
from testlink import TestlinkAPIClient, TestLinkHelper, TestGenReporter
from testlink.testlinkerrors import TLResponseError
import sys, os.path
from platform import python_version  

# precondition a)
# SERVER_URL and KEY are defined in environment
# TESTLINK_API_PYTHON_SERVER_URL=http://YOURSERVER/testlink/lib/api/xmlrpc.php
# TESTLINK_API_PYTHON_DEVKEY=7ec252ab966ce88fd92c25d08635672b
# 
# alternative precondition b)
# SERVEUR_URL and KEY are defined as command line arguments
# python TestLinkExample.py --server_url http://YOURSERVER/testlink/lib/api/xmlrpc.php
#                           --devKey 7ec252ab966ce88fd92c25d08635672b

#set TESTLINK_API_PYTHON_SERVER_URL=http://192.168.56.1/testlink/lib/api/xmlrpc/v1/xmlrpc.php
#set TESTLINK_API_PYTHON_DEVKEY=7f3440df7f7c3e86e82173151d5bba5c

class TEST_LINK(object):
    '''
    CLASS: TEST_LINK
    Description: Create a connection to test link server.
                 Call the api from the testlink
    '''
    def __init__(self):
	    self.tls = testlink.TestLinkHelper().connect(testlink.TestlinkAPIClient)

    def countProjects(self):
        ''' count the number of project on testlink '''
        projs = self.tls.countProjects()
        return projs

    def getProjects(self):
        ''' get all projects with details like id, name etc '''
        projs = self.tls.getProjects()
        return projs

    def getProjectsByName(self, PROJECT_NAME):
        ''' get projects by name '''
        #getTestProjectByName(PROJECT_NAME)
        projs = self.tls.getTestProjectByName(PROJECT_NAME)['id']
        return projs
	
    def getTestSuitByID(self, ID):
        '''Get test suit case by id'''
        suites = self.tls.getTestSuiteByID(ID)
        return suites

    def getTestSuitByName(self, TESTSUITE_NAME):
        ''' get test suites, using the same name'''
        response = self.tls.getTestSuite(TESTSUITE_NAME, "vitthal")
        print("getTestSuite", response)
		
    def getTestPlan(self, PROJECT_ID):
        '''Get TEST Plan by Test Project ID '''
        print(self.tls.getProjectTestPlans(PROJECT_ID))

    def getTestCaseByTestSuite(self, TESTSUITE_ID):
        response = self.tls.getTestCasesForTestSuite(TESTSUITE_ID, True, 'full')
        return(response)

    def getTestCaseByTestPlanID(self, TESTPLAN_ID):
        userid = int(self.tls.getUserByLogin('vitthal')[0]['dbID'])
        response = self.tls.getTestCasesForTestPlan(testplanid=TESTPLAN_ID)
        return(response)

    def getTestCaseByID(self, CASE_ID, VERSION):
        response = self.tls.getTestCase(None,CASE_ID)
        return response
		
    def getTestCaseByName(self, TESTPLAN_NAME, PROJECT_NAME):
        response = self.tls.getTestCaseIDByName(TESTPLAN_NAME, testprojectname=PROJECT_NAME)
        return response

    def getTestCaseStatusByID(self, ID):
        testcase = self.tls.getTestCasesForTestSuite(3, True, 'full')
        return(testcase)	

    def getTestCaseStatusByName(self, TESTPLAN_ID):
        response = self.test.getTestCasesForTestPlan(TESTPLAN_ID, executestatus='f')
        return (response)

    def updateTestCseResult(self,  **kargs):
        pass

if __name__ == '__main__':
    myTestLink = TEST_LINK()
    #print(myTestLink.countProjects())
    #print(myTestLink.getProjects())
    #print(myTestLink.getTestSuitByID(3)) 
    #print(myTestLink.getTestPlanByID(1))
    #print(myTestLink.getTestCaseByTestSuite(3))
    print(myTestLink.getTestCaseByTestPlanID(2))
    #print(myTestLink.getTestCaseByID(1,1))
    #print(myTestLink.getTestCaseStatusByName(2))
    #myTestLink.getTestSuitByName("NewTestPlan")
