import chai from 'chai'
const assert = chai.assert
import VueTestUtils from '@vue/test-utils'


import Formset from '@/forms/formSet.vue'

describe('FormSet', function() {

    let ntfields = {name: {rules: {required: true}}, type: {rules: {required: false}}}

    function getWrapper(initial, fields) {
        let propsData = {fields: fields, initial: initial}
        return VueTestUtils.shallowMount(Formset, {propsData: propsData})
    }

    it('Sets data to initial', function() {
        let fields = {name: {tag: 'input', rules: {required: false}}} 
        let initial = [{name: 'Heck'}, {name: 'Flip'}]
        let wrapper = getWrapper(initial, fields)

        let expectedData = [
            {name: 'Heck', vid: 0, new: false}, 
            {name: 'Flip', vid: 1, new: false}
        ]
        assert.deepEqual(wrapper.vm.formsData, expectedData)
    })

    it('sets default item value correctly', function() {
        let fields = {name: {default: 'wow'}, desc: {}, type: {default: 'swell'}}
        let wrapper = getWrapper([], fields)
        
        let expectedDefault = {name: 'wow', type: 'swell', vid: 0, new: true}
        assert.deepEqual(wrapper.vm.default, expectedDefault)
    })

    it('Maps backend errors to vid', function() {
        let initial = [{name: 'Grape', type: 'Fruit'}, {name: 'lmao', type: 'Abbreviation'}]
        let wrapper = getWrapper(initial, ntfields)
        wrapper.setProps({
            errors: [{name: ['Required']}, {type: ['That type is bad']}]
        })

        let expectedMap = {0: {name: ['Required']}, 1: {type: ['That type is bad']}}
        assert.deepEqual(wrapper.vm.error_map, expectedMap)
    })
    
    it('adds rows', function() {
        let fields = {
            name: {rules: {required: true}, default: 'MyName'}, 
            type: {rules: {required: false}}
        }
        let wrapper = getWrapper([], fields)

        assert.equal(wrapper.vm.formsData.length, 0)
        wrapper.vm.addRow()
        assert.deepEqual(wrapper.vm.formsData, [{name: 'MyName', vid: 0, new: true}])
    })

    it('deletes row', function() {
        let initial = [{name: 'Yes', type: 'Boolean'}, {name: 'No', type: 'Boolean'}]
        let wrapper = getWrapper(initial, ntfields)

        wrapper.vm.deleteRow(1)

        let expectedData = [{name: 'Yes', type: 'Boolean', vid: 0, new: false}]
        assert.deepEqual(wrapper.vm.formsData, expectedData)
    })

    it('doesnt repeat vid values when remove then delete', function() {
        let initial = [{name: 'Yes', type: 'Boolean'}, {name: 'No', type: 'Boolean'}]
        let wrapper = getWrapper(initial, ntfields)

        wrapper.vm.deleteRow(0)
        wrapper.vm.addRow()

        let firstvid = wrapper.vm.formsData[0].vid
        let secondvid = wrapper.vm.formsData[1].vid
        assert.notEqual(firstvid, secondvid)
    })
})
