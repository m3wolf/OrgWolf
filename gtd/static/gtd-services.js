/*globals angular, GtdHeading, jQuery, navigator, window, alert*/
"use strict";

angular.module('owServices')

/*************************************************
* Factory returns an object for showing feedback
* if an operation takes a while. Visual elements
* are rendered using the waitFeedback directive.
*
**************************************************/
.factory('owWaitIndicator', ['$rootScope', function($rootScope) {
    var obj, end_wait;
    // Object contains lists and accessors for those lists
    obj = {
	waitLists: {
	    'quick': [],
	    'medium': [],
	},
	start_wait: function(listName, name) {
	    obj.waitLists[listName].push(name);
	},
	end_wait: function(listName, name) {
	    // First check if the user specified all options or set defaults
	    var lists, i;
	    lists = obj.waitLists[listName];
	    if (lists === undefined) {
		// User didn't specify a list so use all
		name = listName;
		lists = [obj.waitLists.quick, obj.waitLists.medium];
	    } else {
		lists = [lists];
	    }
	    // Clear the specified wait from the lists
	    for (i=0; i<lists.length; i+=1) {
		end_wait(lists[i], name);
	    }
	},
    };
    end_wait = function(list, name) {
	// Helper function for removing items from the list
	var i;
	i = list.indexOf(name);
	while (i > -1) {
	    list.splice(i, 1);
	    i = list.indexOf(name);
	}
    };
    return obj;
}])

/*************************************************
* Factory creates GtdHeading objects
*
**************************************************/
// .factory('OldHeading', ['$resource', '$http', function($resource, $http) {
//     return function(data) {
//         return new GtdHeading(data);
//     };
// }])
.factory('Heading', ['$http', '$resource', 'toaster', function($http, $resource, toaster) {
    var toastOnly, res;
    // Interceptors for manipulating the responses
    toastOnly = {
	'response': function(response) {
	    // Announce a successful save
	    toaster.pop('success', 'Saved');
	    return response;
	},
	'responseError': function(reason) {
	    toaster.pop('error', "Error, not saved!",
			"Check your internet connection and try again");
	    console.log('Save failed:');
	    console.log(reason);
	},
    };
    // Create the actual resource here
    res = $resource(
	'/gtd/nodes/:id/',
	{id: '@id',
	 field_group: '@field_group'},
	{
	    'update': {method: 'PUT', interceptor: toastOnly},
	    'create': {method: 'POST', interceptor: toastOnly},
	}
    );
    return res;
}])

/*************************************************
* Holds the currently accessed Heading, for example
* when the user visits /gtd/projects/#1-work-project
*
**************************************************/
.factory('activeHeading', ['Heading', function(Heading) {
    var HeadingObj;
    HeadingObj = {
	id: 0,
	obj: null
    };
    HeadingObj.activate = function (HeadingId, requestData) {
	var data;
	this.id = parseInt(HeadingId, 10) || 0;
	if (this.id) {
	    data = angular.extend({}, {id: this.id}, requestData);
	    this.obj = Heading.get(data);
	} else {
	    this.obj = null;
	}
    };
    HeadingObj.ifActive = function(callback) {
	if (this.obj) {
	    this.obj.$promise.then(callback);
	}
    };
    return HeadingObj;
}])

/*************************************************
* Default todo states. Override in template from
* server.
*
**************************************************/
.value(
    'todoStatesList',
    [
	{id: 1,
	 color: {
	     red: 0,
	     green: 0,
	     blue: 0,
	     alpha: 0,
	 },
	 abbreviation: 'NEXT',
	},
	{id: 2,
	 color: {
	     red: 0,
	     green: 0,
	     blue: 0,
	     alpha: 0,
	 }
	},
    ]
)

/*************************************************
* Descriptions of A/B/C style priorities
**************************************************/
.value('priorities', [
    {sym: 'A', display: 'A - Critical'},
    {sym: 'B', display: 'B - High'},
    {sym: 'C', display: 'C - Default'}]
)

/*************************************************
* Factory returns the request todoStates
*
**************************************************/
.factory('todoStates', ['$resource', 'todoStatesList', function($resource, todoStatesList) {
    var states, TodoState;
    TodoState = $resource('/gtd/todostates/');
    states = TodoState.query();
    states = todoStatesList;
    states.getState = function(stateId) {
	var foundState, foundStates;
	foundStates = this.filter(function(obj) {
	    return obj.id === stateId;
	});
	if (foundStates.length > 0) {
	    foundState = foundStates[0];
	} else {
	    foundState = null;
	}
	return foundState;
    };
    return states;
}])

/*************************************************
* Factory returns all the available focus areas
*
**************************************************/
.factory('focusAreas', ['$resource', '$rootScope', function($resource, $rootScope) {
    var url, params, focusAreas, i;
    url = '/gtd/focusareas/';
    params = {is_visible: true};
    focusAreas = $resource(url).query(params);
    $rootScope.$on('refresh-data', function() {
	// Remove old focus areas and replace with new ones
	focusAreas.splice(0, focusAreas.length);
	$resource(url).query(params).$promise.then(function(newFocusAreas) {
	    for(i=0; i<newFocusAreas.length; i+=1) {
		focusAreas.push(newFocusAreas[i]);
	    }
	});
    });
    return focusAreas;
}])

.factory('GtdObject', ['$resource', '$rootScope', function($resource, $rootScope) {
    return function(url, params) {
	var objs
	objs = $resource(url).query(params);
	$rootScope.$on('refresh-data', function() {
	    // Remove old objects and replace with new ones
	    contexts.splice(0, objs.length);
	    $resource(url).query(params).$promise.then(function(newObjs) {
		for(i=0; i<newObjs.length; i+=1) {
		    objs.push(newObjs[i]);
		}
	    });
	});
	return objs;
    };
}])

/*************************************************
* Factory returns all the available
* Context objects
*
**************************************************/
.factory('contexts', ['GtdObject', function(GtdObject) {
    return GtdObject('/gtd/contexts', {is_visible: true});
}])

/*************************************************
* Factory returns all the available
* Tag objects
*
**************************************************/
.factory('locations', ['GtdObject', function(GtdObject) {
    return GtdObject('/gtd/locations', {});
}]);
