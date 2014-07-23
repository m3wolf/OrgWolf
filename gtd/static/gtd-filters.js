/*globals angular, $*/
"use strict";


var owFilters = angular.module(
    'owFilters',
    ['ngSanitize', 'owServices']
);

/*************************************************
* Filter that determines relationship to the
* url paramater for target node
*
**************************************************/
owFilters.filter('is_target', function() {
    return function(obj, active) {
	var answer = '';
	if (active) {
	    if ( obj.pk === active.id ) {
		answer = 'yes';
	    } else if ( obj.fields.tree_id === active.tree_id &&
			obj.fields.lft < active.lft &&
			obj.fields.rght > active.rght) {
		// Mark ancestors
		answer = 'ancestor';
	    }
	}
	return answer;
    };
});

/*************************************************
* Filter turns a string into a slug
*
**************************************************/
owFilters.filter('slugify', function() {
    return function(string) {
	var s;
	if (string !== undefined) {
	    /*jslint regexp: true */
	    s = string.toLowerCase().replace(/[^a-z_]/g, '-');
	    /*jslint regexp: false */
	}
	return s;
    };
});

/*************************************************
* Filter that determines style of TodoState object
*
**************************************************/
owFilters.filter('todoStateStyle', function() {
    return function(obj) {
	var style, c;
	style = '';
	if (obj === null || obj === undefined) {
	    style = null;
	} else {
	    /* Set text stylings */
	    c = obj.color;
	    style += 'color: rgba(' + c.red + ', ' + c.green + ', ';
	    style += c.blue + ', ' + c.alpha + '); ';
	}
	return style;
    };
});

/*************************************************
* Filter that determines style of Node object
*
**************************************************/
owFilters.filter('headingStyle', function() {
    return function(obj) {
	var style, colors, color_i;
	style = '';
	// Determine color based on node.rank
	if ( obj.level > 0 ) { // Root headings style by CSS
	    colors = ['rgb(80, 0, 0)', 'rgb(0, 44, 19)',
		      'teal', 'slateblue', 'brown'];
	    color_i = (obj.level) % colors.length;
	    style += 'color: ' + colors[color_i - 1] + '; ';
	}
	return style;
    };
});

/*************************************************
* Sanitizes text to safe HTML
*
**************************************************/
owFilters.filter('asHtml', ['$sce', function($sce) {
    return function(obj) {
	var s = $sce.trustAsHtml(obj);
	return s;
    };
}]);

/*************************************************
* Filter that orders top level headings
*
**************************************************/
owFilters.filter('order', ['$sce', function($sce) {
    return function(obj, criterion) {
	var ordered, deadline, other;
	if ( criterion === 'list' ) {
	    other = obj.filter(function(currHeading) {
		var today, deadline, isOther, delta;
		isOther = false; // Default value
		if (currHeading.deadline_date === null) {
		    // Check for unscheduled heading
		    isOther = true;
		} else {
		    // Check for heading deadline > 7 days in the future
		    today = new Date();
		    deadline = new Date(currHeading.deadline_date);
		    delta = deadline - today;
		    if (delta > (7 * 24 * 3600 * 1000)) {
			isOther = true;
		    }
		}
		return isOther;
	    });
	    deadline = $(obj).not(other).get().order_by('deadline_date');
	    ordered = deadline;
	    ordered = ordered.concat(other.order_by('priority'));
	} else if ( criterion === 'none' ) {
	    ordered = obj;
	} else {
	    ordered = obj.order_by(criterion);
	}
	return ordered;
    };
}]);

/*************************************************
* Filter that only shows headings that are visible
* based on list parameters.
*
**************************************************/
owFilters.filter('currentList', function() {
    return function(headings, todoStates, upcomingList, activeParent) {
	var upcomingListIds;
	// Filter by todoStates
	if ( todoStates ) {
	    headings = headings.filter(function(h) {
		return todoStates.indexOf(h.todo_state) > -1;
	    });
	}
	// Remove headings that are duplicated in the upcomingList
	if ( upcomingList ) {
	    upcomingListIds = upcomingList.map(function(v) {
		return v.id;
	    });
	    headings = headings.filter(function(h) {
		return upcomingListIds.indexOf(h.id) === -1;
	    });
	}
	// Remove headings that aren't descendants of the active parent
	if ( activeParent) {
	    headings = headings.filter(function(h) {
		var isDescendant;
		if (h.tree_id === activeParent.tree_id &&
		    h.lft >= activeParent.lft &&
		    h.rght <= activeParent.rght
		   ) {
		    isDescendant = true;
		} else {
		    isDescendant = false;
		}
		return isDescendant;
	    });
	}
	return headings;
    };
});


/*************************************************
* Filter that displays the deadline for a heading
*
**************************************************/
owFilters.filter('deadline_str', ['$sce', function($sce) {
    return function(deadline, today) {
	var str, date, time_delta, day_delta;
	if ( typeof today === 'undefined' ) {
	    today = new Date();
	}
	str = '';
	if ( deadline ) {
	    str = 'Due ';
	    date = new Date(deadline + 'T12:00:00');
	    today.setHours(12, 0, 0, 0);
	    time_delta = date.getTime() - today.getTime();
	    day_delta = Math.ceil(time_delta / (1000 * 3600 * 24));
	    if ( day_delta === 0 ) {
		// Is today
		str += 'today';
	    } else if (day_delta === -1) {
		// Is yesterday
		str += 'yesterday';
	    } else if (day_delta < 0) {
		// Is farther in the past
		str += Math.abs(day_delta) + ' days ago';
	    } else if (day_delta === 1) {
		// Is tomorrow
		str += 'tomorrow';
	    } else if (day_delta > 0) {
		// Is farther in the future
		str += 'in ' + day_delta + ' days';
	    }
	}
	return str;
    };
}]);

/*************************************************
* Read start and end dates and determine duration
* string.
*
**************************************************/
owFilters.filter('duration', function() {
    return function(node) {
	var str, days, hours, minutes, pluralize, start, end, diff;
	// Calculate relevant duration values
	days = hours = minutes = 0;
	if (node.scheduled_time && node.end_time) {
	    start = new Date(node.scheduled_date + 'T' + node.scheduled_time);
	    end = new Date(node.end_date + 'T' + node.end_time);
	} else {
	    start = new Date(node.scheduled_date);
	    end = new Date(node.end_date);
	}
	diff = end.getTime() - start.getTime();
	days = Math.floor(diff / (1000 * 3600 * 24));
	diff = diff % (1000 * 3600 * 24);
	hours = Math.floor(diff / (1000 * 3600));
	diff = diff % (1000 * 3600);
	minutes = Math.floor(diff / (1000 * 60));
	// Construct duration string
	pluralize = function(num, singular, plural) {
	    var s = '';
	    if (num) {
		s += num + ' ';
		if (Math.abs(num) > 1) {
		    s += plural;
		} else {
		    s += singular;
		}
		s += ', ';
	    }
	    return s;
	};
	str = '';
	if (days) {
	    str += pluralize(days, 'day', 'days');
	}
	if (hours) {
	    str += pluralize(hours, 'hour', 'hours');
	}
	if (minutes) {
	    str += pluralize(minutes, 'minute', 'minutes');
	}
	// Clean up any remaining ", " at the end of the string
	str = str.substring(0, str.length-2);
	return str;
    };
});

/*************************************************
* Filter a list (of headings) by the active
* focus area
*
**************************************************/
owFilters.filter('currentFocusArea', ['$rootScope', function($rootScope) {
    return function(oldList, activeFocusArea) {
	var i, newList, activeId;
	// Get id of active focus area if not supplied by caller
	if (typeof activeFocusArea === 'undefined' && $rootScope.activeFocusArea) {
	    activeId = parseInt($rootScope.activeFocusArea.id, 10);
	} else if (activeFocusArea) {
	    // Filter by the active focus area
	    activeId = parseInt(activeFocusArea.id, 10);
	} else {
	    activeId = 0;
	}
	// Now do the actual filtering
	if (activeId) {
	    newList = [];
	    for (i=0; i<oldList.length; i+=1) {
		if( oldList[i].focus_areas.indexOf(activeId) > -1 ) {
		    newList.push(oldList.slice(i, i+1)[0]);
		}
	    }
	} else {
	    newList = oldList.slice(0);
	}
	return newList;
    };
}]);

/*************************************************
* Filter accepts a heading and returns a string of
* its focus areas
*
**************************************************/
owFilters.filter('listFocusAreas', ['focusAreas', function(focusAreas) {
    return function(heading) {
	var s, f, i, fa, activeFocusAreas, areaName;
	// Build list of focus area names
	activeFocusAreas = [];
	f = function(fa) {return fa.id === heading.focus_areas[i];};
	for (i=0; i<heading.focus_areas.length; i+=1) {
	    areaName = focusAreas.filter(f)[0];
	    activeFocusAreas.push(areaName);
	}
	// Combine focus area names into a string
	s = '';
	for (i=0; i<activeFocusAreas.length; i+=1) {
	    fa = activeFocusAreas[i];
	    if (i===0) {
		// First entry
		s += fa.display;
	    } else if (i===(activeFocusAreas.length-1) &&
		       activeFocusAreas.length > 1) {
		// Last entry
		s += ' and ' + fa.display;
	    } else {
		// All other entries
		s += ', ' + fa.display;
	    }
	}
	return s;
    };
}])

/*************************************************
* Filter takes a string and wraps the search
* query in a span element
*
**************************************************/
.filter('highlightSearch', [function() {
    return function(sourceString, reString) {
	var i, regex;
	// Now apply the regular expression and wrap text
	regex = new RegExp(reString, "ig");
	sourceString = sourceString.replace(
	    regex,
	    '<span class="highlight">$&</span>'
	);
	return sourceString;
    };
}])

/*************************************************
* Filter takes text, trims it down then highlights
* the matched queries.
*
**************************************************/
.filter('highlightSearchText', [function() {
    return function(sourceText, reString) {
	var regex, workingString, firstMatch;
	// First remove html tags
	/*jslint regexp: true*/
	sourceText = String(sourceText).replace(/<[^>]+>/gm, '');
	/*jslint regexp: false*/
	// Process the string
	regex = new RegExp(reString, "ig");
	firstMatch = sourceText.search(regex);
	if (firstMatch > -1) {
	    // Truncate extra text at the front
	    if (firstMatch > 40) {
		sourceText = '&hellip;' + sourceText.slice(firstMatch-40);
	    }
	    // Restrict total length
	    if (sourceText.length > 500) {
		sourceText = sourceText.slice(0, 500);
		sourceText += '&hellip;';
	    }
	} else { // No match so return empty string
	    sourceText = '';
	}
	return sourceText;
    };
}]);
