import favouriteComponent from '@/favourite.vue'
import simpleList from '@/simpleList.vue'
import tagsModal from '@/tagsModal.vue'
import linksDisplay from '@/linksDisplay.vue'
import issueModal from '@/issueModal.vue'

export default {
    el: '#vue-container',
    components: {
        'simple-list': simpleList,
        'favourite': favouriteComponent,
        'tags-modal': tagsModal,
        'links-display': linksDisplay,
        'issue-modal': issueModal
    },
    data: {
        saved_tags: [],
        tagsModalOpen: false,
        issueModalOpen: false,
    },
    methods: {
        openTagsModal: function() {
            this.tagsModalOpen = true
        },
        closeTagsModal: function() {
            this.tagsModalOpen = false
        },
        openIssuesModal: function() {
            this.issueModalOpen = true
        },
        closeIssuesModal: function() {
            this.issueModalOpen = false
        },
        updateTags: function(tags) {
            this.saved_tags = tags
            this.tagsModalOpen = false
        }
    }
}