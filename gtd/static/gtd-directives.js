import jQuery from "jquery";
import 'jquery';
window.jQuery = jQuery;
window.$ = jQuery;
import 'gtd-filters';
import 'jquery-ui-dist/jquery-ui';

import 'bootstrap/dist/js/bootstrap.js';

import 'bootstrap-switch/dist/js/bootstrap-switch.js';


import "angular";
import "angular-animate";
import "angular-resource";
import "angular-cookies";

import EasyMDE from 'easymde';

"use strict";

angular.module('owDirectives')

/*************************************************
* Directive modifies the DOM after calls to
* waitIndicator service
*
**************************************************/
.directive('owWaitFeedback', ['owWaitIndicator', function(owWaitIndicator) {
    // Directive creates the pieces that allow the user to edit a heading
    function link($scope, $element, attrs) {
	$scope.short_wait = false;
	$scope.long_wait = false;
	// Respond to each waiting list by showing the appropriate setting
	$scope.$watchCollection(
	    function() { return owWaitIndicator.waitLists.quick.length; },
	    function(newLength) {
		$scope.short_wait = (newLength > 0);
	    }
	);
	$scope.$watchCollection(
	    function() { return owWaitIndicator.waitLists.medium.length; },
	    function(newLength) {
		$scope.long_wait = (newLength > 0);
	    }
	);
    }
    return {
	link: link,
	scope: {},
    };
}])

/*************************************************
* Directive that lets a user change the current
* active date for lists and inbox
*
**************************************************/
.directive('owCurrentDate', function() {
    // Directive creates the pieces that allow the user to edit a heading
    function link($scope, $element, attrs) {
	var $input;
	$input = $element.find('input');
	$scope.isEditable = false;
	// Set some strings for the DOM
	function set_strings(newDate) {
	    $scope.dateString = newDate.toDateString();
	    $scope.dateModel = newDate.ow_date();
	    $scope.dateModel = newDate;
	    return newDate;
	}
	// Setup the widget based on parent scope's current_date
	$scope.$watch('currentDate', function(newDate) {
	    return set_strings(newDate);
	}, true);
	// When the input loses focus, update the parent scope currentDate
	$input.on('blur', function() {
	    $scope.$apply(function() {
		var newDate;
		$scope.isEditable = false;
		newDate = new Date($scope.dateModel);
		if ( isNaN(newDate) ) {
		    // invalid date: reset values
		    set_strings($scope.currentDate);
		} else {
		    // Valid date: update parent scope (valid dates only)
		    $scope.currentDate.setDate(newDate.getUTCDate());
		    $scope.currentDate.setMonth(newDate.getUTCMonth());
		    $scope.currentDate.setYear(newDate.getUTCFullYear());
		}
	    });
	});
    }
    return {
	link: link,
	templateUrl: '/static/current-date.html',
	scope: true,
    };
})

/*************************************************
* Directive that shows the details of a node
*
**************************************************/
.directive('owDetails', [function() {
    function link(scope, element, attrs) {
	// Get the full set of model fields
	scope.heading.$get()
    }
    return {
	link: link,
	scope: { heading: '=owHeading' },
	templateUrl: '/static/details.html'
    };
}])

/*************************************************
* Directive that lets a user edit a node.
* The ow-heading attr indicates that heading is
* being edited. The ow-parent attr indicates this
* is a new child.
*
**************************************************/
.directive('owEditable', ['$resource', '$rootScope', '$timeout', 'owWaitIndicator', 'Heading', 'todoStates', 'focusAreas', 'priorities', 'toaster', 'toDateObjFilter', 'decodeHtmlFilter', function($resource, $rootScope, $timeout, owWaitIndicator, Heading, todoStates, focusAreas, priorities, toaster, toDateObjFilter, decodeHtml) {
    // Directive creates the pieces that allow the user to edit a heading
    function link(scope, element, attrs) {
	var defaultParent, $text, heading, $save, $titleInput, heading_id, parent, editorId;
	scope.focusAreas = focusAreas;
	scope.todoStates = todoStates;
	scope.fields = {};
	element.addClass('ow-editable'); // For animations
	// Set some initial field values
	if ( scope.heading ) {
	    // Get the full fieldset if an existing heading is being edited
	    // Initiate wait indicator
	    owWaitIndicator.start_wait('quick', 'editable');
	    // Retrieve object from API
	    scope.fields = Heading.get({id: scope.heading.id});
	    scope.fields.$promise.then(function() {
		var field, dateFields, i;
		owWaitIndicator.end_wait('editable');
		dateFields = ['scheduled_date', 'deadline_date', 'end_date']
		// Cycle through each field and convert the date
		for (i=0; i<dateFields.length; i+=1) {
		    field = dateFields[i];
		    scope.fields[field] = toDateObjFilter(scope.fields[field]);
		}
		// Unescape the HTML so we can edit it
		scope.fields['text'] = decodeHtml(scope.fields['text']);
	    });
	} else if ( scope.parent ) {
	    // Initiate wait indicator
	    owWaitIndicator.start_wait('quick', 'editable');
	    // Refresh the parent object with more fields
	    scope.parent = Heading.get({id: scope.parent.id});
	    scope.parent.$promise.then(function() {
		var field, dateFields, i;
		owWaitIndicator.end_wait('editable');
		dateFields = ['scheduled_date', 'deadline_date', 'end_date']
		// Inherit some attributes from parent...
		scope.fields.focus_areas = scope.parent.focus_areas;
		scope.fields.priority = scope.parent.priority;
		scope.fields.parent = scope.parent.id;
		scope.fields.deadline_date = scope.parent.deadline_date;
		scope.fields.deadline_time = scope.parent.deadline_time;
		scope.fields.scheduled_date = scope.parent.scheduled_date;
		scope.fields.scheduled_time = scope.parent.scheduled_time;
		scope.fields.text = '';
		scope.fields.title = '';
		// Cycle through each field and convert the date
		for (i=0; i<dateFields.length; i+=1) {
		    field = dateFields[i];
		    scope.fields[field] = toDateObjFilter(scope.fields[field]);
		}
	    });
	} else {
	    // ...or use defaults if no parent
	    scope.fields.focus_areas = [];
	    scope.fields.priority = 'C';
	    scope.fields.text = '';
	    scope.fields.title = '';
	    // Set Scope if a tab is active
	    if ($rootScope.activeFocusArea && $rootScope.activeFocusArea.id > 0) {
		scope.fields.focus_areas.push($rootScope.activeFocusArea.id);
	    }
	}
	scope.priorities = priorities;
	scope.time_units = [
	    {value: 'd', label: 'Days'},
	    {value: 'w', label: 'Weeks'},
	    {value: 'm', label: 'Months'},
	    {value: 'y', label: 'Years'},
	];
	// Option for repeats_from_completion field
	scope.repeat_schemes = [
	    {value: false, label: 'scheduled date'},
	    {value: true, label: 'completion date'},
	];
	$text = element.find('.edit-text');
	$save = element.find('#edit-save');
	// Scroll so element is in view
	$('html').animate({scrollTop: element.offset().top - 27}, '500');
	// Event handlers for the editable dialog
	scope.save = function(e) {
	    var newHeading;
	    // When the user saves the edited heading
	    if ( scope.heading ) {
		newHeading = Heading.update(scope.fields);
	    } else {
		newHeading = Heading.create(scope.fields);
	    }
	    newHeading.$promise.then(function(data) {
	    	scope.endEdit(newHeading);
	    });
	};
	// Prepare the markdown editor
	var textArea = element.find('.edit-text');
	if ($(textArea).length > 0) {
	    scope.editor = new EasyMDE({
		element: $(textArea)[0],
	    });
	    scope.editor.codemirror.on("change", function() {
		// Save the heading text when changed
		if (scope.fields.text != scope.editor.value()) {
		    scope.fields.text = scope.editor.value();
		    scope.$apply();
		}
	    });
	    scope.$watch('fields.text', function(newText, oldText, currScope) {
		// Update the editor when the model changes
		if (currScope.editor.value() != newText) {
		    currScope.editor.value(newText);
		}
	    });
	} // end of markdown editor preparation
	// Process the callbacks for when editing is done
	scope.cancelEdit = function(e) {
	    scope.endEdit(null);
	};
	scope.endEdit = function(newHeading) {
	    scope.$emit('finishEdit', newHeading);
	    scope.$parent.$parent.$eval(scope.finishCallback);
	};
	// Focus the title element so it can be edited
	$titleInput = element.find('#title');
	console.log(scope.fields);
	if ( scope.fields.title == '' ) {
	    $titleInput.focus();
	}
    }
    return {
	link: link,
	scope: {
	    heading: '=owHeading',
	    parent: '=owParent',
	    finishCallback: '@owEditFinish',
	},
	require: '?ngModel',
	templateUrl: '/static/editable.html'
    };
}])

/*************************************************
* Directive that a heading drag-n-drop draggable
* (uses jQuery ui)
**************************************************/
.directive('owDraggable', [function() {
    function link(scope, element, attrs) {
	var options, dragDropData;
	dragDropData = {};
	options = {
	    handle: '> .ow-hoverable',
	    // containment: '.outline',
	    zIndex: 9999,
	    helper: 'clone',
	    revert: 'invalid',
	    start: function(event, ui) {
		// Save some context data about the draggable
		dragDropData.list = scope.children;
		dragDropData.heading = scope.heading;
		$(element).data('dragDrop', dragDropData);
	    },
	};
	jQuery(element).draggable(options);
    }
    return {
	link: link,
	scope: false,
    };
}])

/*************************************************
* Directive that a heading drag-n-drop droppable
* for ow-draggable elements
* (uses jQuery ui)
**************************************************/
.directive('owDroppable', [function() {
    function link(scope, element, attrs) {
	var openTwisty, options;
	options = {
	    drop: function(event, ui) {
		var data, oldIdx, heading, oldList, newList;
		// Get context data from the draggable
		data = $(ui.draggable).data('dragDrop');
		heading = data.heading;
		oldList = data.list;
		oldIdx = oldList.indexOf(heading);
		// Set the new parent
		var newParent = scope.heading;
		heading.parent = newParent ? newParent.id : null;
		heading.$update()
		    .then(function() {
			// Remove from old list and refresh the new list
			oldList.splice(oldIdx, 1);
			scope.loadedChildren = false;
			scope.getChildren();
		    });
	    },
	    /* Visual feedback for droppability */
	    over: function(event, ui) {
		element.addClass('droppable-over');
		// Open the tab if the user hovers for a short period
		var interval = 1000 // in milliseconds
		openTwisty = setTimeout(function() {
		    scope.$apply(function() {
			scope.toggleHeading(1);
		    });
		}, interval);
	    },
	    out: function(event, ui) {
		element.removeClass('droppable-over');
		clearTimeout(openTwisty);
	    },
	    activate: function(event, ui) {
		element.addClass('droppable-active');
	    },
	    deactivate: function(event, ui) {
		element.removeClass('droppable-active');
		element.removeClass('droppable-over');
	    },
	};
	// Function to identify ridiculous moves, like making a
	// heading its own parent
	scope.isValidMove = function() {
	};
	jQuery(element).droppable(options);
    }
    return {
	link: link,
	scope: false,
    };
}])

/*************************************************
* Directive that shows a list of FocusArea tabs.
* When a tab is clicked, this directive emits the
* 'focus-area-changed' signal via the scope's $emit()
* method with the new focus area as the first argument.
*
**************************************************/
.directive('owFocusAreaTabs', ['$resource', '$rootScope', '$timeout', 'focusAreas', function($resource, $rootScope, $timeout, focusAreas) {
    // Directive creates tabs that allow a user to filter by focus area
    function link(scope, element, attrs) {
	scope.allFocusArea = {
	    id: 0,
	    display: 'All'
	};
	scope.noneFocusArea = {
	    id: -1,
	    display: 'None'
	};
	scope.focusAreas = focusAreas;
	scope.activeFocusArea = scope.allFocusArea;
	$rootScope.activeFocusArea = scope.allFocusArea;
	$timeout(function() {
	    element.find('#fa-tab-0').addClass('active');
	});
	// Tab click handler
	scope.changeFocusArea = function(newFocusArea) {
	    // Update UI
	    element.find('#fa-tab-' + scope.activeFocusArea.id).removeClass('active');
	    scope.activeFocusArea = newFocusArea;
	    $rootScope.activeFocusArea = newFocusArea;
	    element.find('#fa-tab-' + scope.activeFocusArea.id).addClass('active');
	    // Send the relevant signals
	    $rootScope.$broadcast('focus-area-changed', newFocusArea);
	};
    }
    return {
	link: link,
	scope: {},
	templateUrl: '/static/focus-area-tabs.html'
    };
}])

/*************************************************
* Directive that lets a user change the todo state
* with a popover menu
**************************************************/
.directive('owTodo', ['$rootScope', '$filter', 'todoStates', 'toaster', function($rootScope, $filter, todoStates, toaster) {
    // Directive creates the pieces that allow the user to edit a heading
    function link(scope, element, attrs) {
	var i, $span, $popover, $options, state, content, s, isInitialized;
	element.addClass("todo-state-widget");
	scope.todoState = todoStates.getState(scope.heading.todo_state);
	scope.todoStateId = scope.heading.todo_state;
	scope.$watch('todoStateId', function(newStateId, oldStateId) {
	    // When the todoStateId changes (by user action)
	    if (newStateId !== scope.heading.todo_state) {
		var oldDate;
		scope.heading.todo_state = parseInt(newStateId, 10);
		scope.todoState = todoStates.getState(scope.heading.todo_state);
		scope.heading.auto_update = true;
		oldDate = scope.heading.scheduled_date;
		scope.heading.$update()
		    .then(function(response) {
			if (scope.todoState != null) {
			    scope.$emit('finishEdit', response.data,
					scope.todoState.closed);
			}
			if (response.data.scheduled_date !== oldDate) {
			    // Notify the user that the heading is rescheduled
			    var s = 'Rescheduled for ';
			    s += response.data.scheduled_date;
			    toaster.pop('info', null, s);
			}
		    });
	    }
	});
	scope.$watch(
	    function() { return scope.heading.todo_state; },
	    function(newHeadingStateId) {
		if (newHeadingStateId !== scope.todoStateId) {
		    scope.todoState = todoStates.getState(scope.heading.todo_state);
		    scope.todoStateId = newHeadingStateId;
		}
		// Attach a tooltip with the states text
		if (scope.todoState) {
		    element.tooltip({
			delay: {show:1000, hide: 100},
			title: scope.todoState.display_text,
		    });
		}
	    }
	);
    }
    function compile(cElement, cAttrs) {
	// Create the <option> element for each todoState
	var select, i, h, todoState;
	select = cElement.find('select');
	for (i=0; i<todoStates.length; i+=1) {
	    todoState = todoStates[i];
	    h = '<option value="' + todoState.id + '" ';
	    h += 'style="' + $filter('todoStateStyle')(todoState) + '">';
	    h += todoState.abbreviation + '</option>';
	    select.append(h);
	}
	return link;
    }
    return {
	compile: compile,
	scope: {
	    heading: '=owHeading'
	},
	templateUrl: '/static/todo-state-selector.html',
    };
}])

/*************************************************
* Directive forms a node in an outline (and takes
* care of any child nodes).
*
**************************************************/
.directive('owTwisty', ['$compile', '$rootScope', 'Heading', 'activeHeading', function($compile, $rootScope, Heading, activeHeading) {
    function link(scope, element, attrs) {
	var hoverable, get_children;
	scope.isEditing = false;
	scope.loadedChildren = false;
	scope.state = 0;
	element.addClass('state-'+scope.state);
	scope.showArchived = $rootScope.showArchived;
	// Get todo-states
	if ($rootScope.todoStates) {
	    scope.todoStates = $rootScope.todoStates;
	} else {
	    scope.todoStates = [];
	}
	if ( scope.todoState && scope.todoState.actionable ) {
	    element.find('.ow-hoverable').addClass('actionable');
	}
	scope.$on('toggle-archived', function(e, newState) {
	    scope.showArchived = newState;
	});
	if ( scope.heading.level === 0 ) {
	    element.find('.ow-hoverable').addClass('project');
	}
	element.addClass('heading');
	hoverable = element.children('.ow-hoverable');
	// Process tag_string into tags
	scope.tags = scope.heading.tag_string.slice(1, -1).split(':');
	// Test for expandability
	scope.$watch(
	    'heading.rght - heading.lft',
	    function(newDiff) {
		if (newDiff > 1) {
		    hoverable.removeClass('leaf-node');
		    scope.isLeafNode = false;
		} else {
		    hoverable.addClass('leaf-node');
		    scope.isLeafNode = true;
		}
	    }
	);
	// Handler for getting the children of this heading
	scope.getChildren = function() {
	    if (!scope.loadedChildren) {
		scope.children = Heading.query({parent_id: scope.heading.id,
						field_group: 'outline'});
		scope.children.$promise.then(function(headings) {
		    scope.numArchived = headings.filter(function(obj) {
			return obj.archived === true;
		    }).length;
		    scope.loadedChildren = true;
		});
	    }
	};
	scope.$on('open-descendants', function(e) {
	    if (e.targetScope !== e.currentScope) {
		scope.toggleHeading(1);
	    }
	});
	// Get children if this is not a root level node
	if (scope.heading.level > 0) {
	    scope.getChildren();
	}
	// Handlers for clicking on the heading (may be overridden by components)
	scope.toggleHeading = function(newState) {
	    // 0 is closed, 1 is partly open, 2 is fully open
	    element.removeClass('state-' + scope.state);
	    if ( /^\d+$/.test(newState) ) {
		// Specific state is passed as an integer
		scope.state = newState % 3;
	    }
	    else if ($(newState.target).is(':not(.non-opening)')) {
		// Verify that something should be toggled
		scope.state = (scope.state + 1) % 3;
		// Skip state 1 for leaf nodes
		if (scope.isLeafNode && scope.state === 1) {
		    scope.state = 2;
		}
	    }
	    element.addClass('state-' + scope.state);
	    // Get children if heading is now open
	    if (scope.state > 0) {
		scope.getChildren();
	    }
	    if (scope.state === 2) {
		scope.$broadcast('open-descendants');
	    }
	};
	// Handler for clicking the "edit" button
	scope.edit = function(e) {
	    var $off;
	    e.stopPropagation();
	    scope.isEditing = true;
	    $off = scope.$on('finishEdit', function(event, newHeading) {
		// Emitted by the owEditable when hiding the editable
		scope.isEditing = false;
		event.stopPropagation();
		if ( newHeading ) {
		    // Update existing heading
		    angular.extend(scope.heading, newHeading);
		    if ( scope.heading.todo_state ) {
			scope.todoState = scope.todoStates.filter(function(state) {
			    return state.id === scope.heading.todo_state;
			})[0];
		    } else {
			scope.todoState = null;
		    }
		}
		$off();
	    });
	};
	// Handler for clicking the "new child" button
	scope.createChild = function(e) {
	    var $off;
	    e.stopPropagation();
	    // Open the twisty if necessary
	    if ( scope.state === 0 ) {
		scope.toggleHeading(1);
	    }
	    scope.newChild = true;
	    $off = scope.$on('finishEdit', function(event, newHeading) {
		// Emitted by the owEditable when hiding the editable
		scope.newChild = false;
		event.stopPropagation();
		if ( newHeading ) {
		    // Add new child to the list
		    scope.children.push(newHeading);
		}
		$off();
	    });
	};
	// Handler for toggling the visibility (archive) of a node
	scope.archive = function(e) {
	    e.stopPropagation();
	    scope.heading.archived = !scope.heading.archived;
	    scope.heading.$update();
	};
	// Check if this node is related to the active Node
	activeHeading.ifActive(function(activeObj) {
	    var isAncestor = (activeObj.tree_id === scope.heading.tree_id &&
			      activeObj.lft > scope.heading.lft &&
			      activeObj.rght < scope.heading.rght);
	    if (activeObj.id === scope.heading.id) {
		// This is the actual heading
		element.addClass('active-heading');
	    } else if (isAncestor) {
		// This is an ancestor of activeHeading and should be open
		scope.toggleHeading(1);
	    }
	});
    }
    // Special compile function that avoids a recursive dead-lock
    function compile(tElement, tAttr) {
        var compiledContents, contents;
        contents = tElement.contents().remove();
        return function(scope, iElement, iAttr) {
            if(!compiledContents) {
                compiledContents = $compile(contents);
            }
            compiledContents(scope, function(clone, scope) {
                iElement.append(clone);
		// Now call our own link function
		link(scope, iElement, iAttr);
            });
        };
    }
    return {
	// link: link,
	compile: compile,
	templateUrl: '/static/outline-twisty.html',
	scope: {
	    heading: '=owHeading',
	},
    };
}])

/*************************************************
* Directive sets the parameters of next
* actions table row
**************************************************/
.directive('owListRow', ['$rootScope', 'todoStates', '$filter', function($rootScope, todoStates, $filter) {
    function link(scope, element, attrs) {
	var node_pk, $element;
	$element = $(element);
	element.addClass("heading-row");
	element.addClass('priority' + (scope.heading.priority || 'B'));
	// Get heading's todoState
	scope.todoState = todoStates.getState(scope.heading.todo_state);
	// Process tag_string into tags
	scope.tags = scope.heading.tag_string.slice(1, -1).split(':');
	// Determine bootstrap row style based on overdue status
	scope.$watch(
	    function() {return scope.heading.deadline_date;},
	    function(newDeadline) {
		var row_cls;
		if ( newDeadline ) {
		    scope.owDate = $filter('deadline_str')(newDeadline);
		}
		element.removeClass('overdue');
		element.removeClass('upcoming');
		row_cls = $filter('deadline_class')(newDeadline);
		element.addClass(row_cls);
	    }
	);
	// CSS class based on archived status
	scope.$watch(
	    'heading.fields.archived',
	    function(archived) {
		if (archived) {
		    element.addClass('archived');
		}
	    }
	);
	// CSS class based on priority
	scope.$watch(
	    'heading.fields.priority',
	    function(new_priority, old_priority) {
		// Remove old CSS class
		if (old_priority) {
		    element.removeClass('priority-' + old_priority);
		}
		// And add new one
		if (new_priority) {
		    element.addClass('priority-' + new_priority);
		}
	    }
	);
	// Handlers for action buttons
	scope.edit = function() {
	    var $off;
	    scope.isEditable = true;
	    $off = scope.$on('finishEdit', function(e) {
		scope.isEditable = false;
		$off();
	    });
	};
	// Response when user edits the heading
	scope.$on('finishEdit', function(e, newHeading, completed) {
	    e.stopPropagation();
	    angular.extend(scope.heading, newHeading);
	    scope.completed = completed;
	});
    }
    return {
	link: link,
	scope: {
	    heading: '=owHeading',
	    owDate: '@',
	},
	templateUrl: '/static/actions-list-row.html',
    };
}]);
