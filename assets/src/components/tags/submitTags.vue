<template>
  <button id="tag-editor-submit" type="button" class="btn btn-primary" @click="submit_tags">Save changes</button>
</template>

<script>
import { addHeaderMessage } from 'src/lib/messages.js'
import apiRequest from 'src/mixins/apiRequest.js'

export default {
    props: ['submitUrl', 'tags'],
    mixins: [apiRequest],
    data: () => ({
        message: 'Tags Saved',
    }),
    methods: {
        submit_tags: function() {
            var data = {
                tags: this.tagsList,
            }

            this.put(this.submitUrl, data)
            .then((response) => {
                addHeaderMessage(this.message)
                this.$emit('tags-saved', response.data['tags'])
            })
        }
    },
    watch: {
        errors: function(value) {
            this.$emit('errors', value)
        }
    },
    computed: {
        tagsList: function() {
            let list = []
            for (let tagname of this.tags) {
                list.push({name: tagname})
            }
            return list
        }
    }
}
</script>
